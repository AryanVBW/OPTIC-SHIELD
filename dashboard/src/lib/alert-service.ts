import { Detection } from '@/types'
import { getTwilioService } from './twilio-service'
import { getSendGridService } from './sendgrid-service'

export interface AlertRecipient {
    id: string
    name: string
    phone?: string
    email?: string
    preferredChannels: ('whatsapp' | 'sms' | 'email')[]
    active: boolean
    createdAt: string
}

export interface AlertMessage {
    id: string
    detectionId: number
    recipientId: string
    recipientName: string
    channel: 'whatsapp' | 'sms' | 'email'
    status: 'pending' | 'sent' | 'failed' | 'delivered'
    sentAt?: string
    deliveredAt?: string
    error?: string
}

export interface BulkAlertRequest {
    detectionIds: number[]
    recipientIds: string[]
    channels: ('whatsapp' | 'sms' | 'email')[]
    customMessage?: string
}

export interface BulkAlertProgress {
    total: number
    sent: number
    failed: number
    current?: string
}

export class AlertService {
    private recipients: Map<string, AlertRecipient> = new Map()
    private alertHistory: AlertMessage[] = []
    private twilioService = getTwilioService()
    private sendGridService = getSendGridService()

    constructor() {
        // Initialize with some demo recipients
        this.addRecipient({
            name: 'Demo User',
            phone: '+1234567890',
            email: 'demo@example.com',
            preferredChannels: ['email'],
            active: true,
        })
    }

    /**
     * Add a new alert recipient
     */
    addRecipient(data: Omit<AlertRecipient, 'id' | 'createdAt'>): AlertRecipient {
        const recipient: AlertRecipient = {
            ...data,
            id: this.generateId(),
            createdAt: new Date().toISOString(),
        }

        this.recipients.set(recipient.id, recipient)
        return recipient
    }

    /**
     * Update an existing recipient
     */
    updateRecipient(id: string, data: Partial<Omit<AlertRecipient, 'id' | 'createdAt'>>): AlertRecipient | null {
        const recipient = this.recipients.get(id)
        if (!recipient) return null

        const updated = { ...recipient, ...data }
        this.recipients.set(id, updated)
        return updated
    }

    /**
     * Delete a recipient
     */
    deleteRecipient(id: string): boolean {
        return this.recipients.delete(id)
    }

    /**
     * Get a recipient by ID
     */
    getRecipient(id: string): AlertRecipient | null {
        return this.recipients.get(id) || null
    }

    /**
     * Get all recipients
     */
    getAllRecipients(): AlertRecipient[] {
        return Array.from(this.recipients.values())
    }

    /**
     * Get active recipients
     */
    getActiveRecipients(): AlertRecipient[] {
        return this.getAllRecipients().filter(r => r.active)
    }

    /**
     * Send alert to a single recipient via specific channel
     */
    async sendAlert(
        recipient: AlertRecipient,
        detection: Detection,
        channel: 'whatsapp' | 'sms' | 'email',
        customMessage?: string
    ): Promise<AlertMessage> {
        const message: AlertMessage = {
            id: this.generateId(),
            detectionId: detection.id,
            recipientId: recipient.id,
            recipientName: recipient.name,
            channel,
            status: 'pending',
        }

        try {
            let result: { success: boolean; messageId?: string; error?: string }

            switch (channel) {
                case 'whatsapp':
                    if (!recipient.phone) {
                        throw new Error('Recipient does not have a phone number')
                    }
                    result = await this.twilioService.sendWhatsAppAlert(recipient.phone, detection, customMessage)
                    break

                case 'sms':
                    if (!recipient.phone) {
                        throw new Error('Recipient does not have a phone number')
                    }
                    result = await this.twilioService.sendSMSAlert(recipient.phone, detection, customMessage)
                    break

                case 'email':
                    if (!recipient.email) {
                        throw new Error('Recipient does not have an email address')
                    }
                    result = await this.sendGridService.sendEmailAlert(recipient.email, detection, customMessage)
                    break

                default:
                    throw new Error(`Unknown channel: ${channel}`)
            }

            if (result.success) {
                message.status = 'sent'
                message.sentAt = new Date().toISOString()
            } else {
                message.status = 'failed'
                message.error = result.error
            }
        } catch (error: any) {
            message.status = 'failed'
            message.error = error.message || 'Unknown error'
        }

        this.alertHistory.push(message)
        return message
    }

    /**
     * Send bulk alerts
     */
    async sendBulkAlerts(
        request: BulkAlertRequest,
        detections: Detection[],
        onProgress?: (progress: BulkAlertProgress) => void
    ): Promise<{ messages: AlertMessage[]; summary: { total: number; sent: number; failed: number } }> {
        const messages: AlertMessage[] = []
        let totalMessages = 0
        let sentCount = 0
        let failedCount = 0

        // Calculate total messages
        totalMessages = request.detectionIds.length * request.recipientIds.length * request.channels.length

        for (const detectionId of request.detectionIds) {
            const detection = detections.find(d => d.id === detectionId)
            if (!detection) continue

            for (const recipientId of request.recipientIds) {
                const recipient = this.recipients.get(recipientId)
                if (!recipient || !recipient.active) continue

                for (const channel of request.channels) {
                    // Send alert
                    const message = await this.sendAlert(recipient, detection, channel, request.customMessage)
                    messages.push(message)

                    if (message.status === 'sent') {
                        sentCount++
                    } else {
                        failedCount++
                    }

                    // Report progress
                    if (onProgress) {
                        onProgress({
                            total: totalMessages,
                            sent: sentCount,
                            failed: failedCount,
                            current: `Sending ${channel} to ${recipient.name}...`,
                        })
                    }

                    // Small delay between messages
                    await new Promise(resolve => setTimeout(resolve, 500))
                }
            }
        }

        return {
            messages,
            summary: {
                total: totalMessages,
                sent: sentCount,
                failed: failedCount,
            },
        }
    }

    /**
     * Get alert history
     */
    getAlertHistory(limit?: number): AlertMessage[] {
        const history = [...this.alertHistory].reverse()
        return limit ? history.slice(0, limit) : history
    }

    /**
     * Get alert history for a specific recipient
     */
    getRecipientAlertHistory(recipientId: string, limit?: number): AlertMessage[] {
        const history = this.alertHistory
            .filter(m => m.recipientId === recipientId)
            .reverse()
        return limit ? history.slice(0, limit) : history
    }

    /**
     * Get alert statistics
     */
    getAlertStats(): {
        totalSent: number
        totalFailed: number
        byChannel: Record<string, { sent: number; failed: number }>
        recentAlerts: AlertMessage[]
    } {
        const stats = {
            totalSent: 0,
            totalFailed: 0,
            byChannel: {} as Record<string, { sent: number; failed: number }>,
            recentAlerts: this.getAlertHistory(10),
        }

        for (const message of this.alertHistory) {
            if (message.status === 'sent') {
                stats.totalSent++
            } else if (message.status === 'failed') {
                stats.totalFailed++
            }

            if (!stats.byChannel[message.channel]) {
                stats.byChannel[message.channel] = { sent: 0, failed: 0 }
            }

            if (message.status === 'sent') {
                stats.byChannel[message.channel].sent++
            } else if (message.status === 'failed') {
                stats.byChannel[message.channel].failed++
            }
        }

        return stats
    }

    /**
     * Check service availability
     */
    getServiceStatus(): {
        whatsapp: boolean
        sms: boolean
        email: boolean
    } {
        return {
            whatsapp: this.twilioService.isConfigured(),
            sms: this.twilioService.isConfigured(),
            email: this.sendGridService.isConfigured(),
        }
    }

    /**
     * Generate unique ID
     */
    private generateId(): string {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    }

    /**
     * Validate recipient data
     */
    validateRecipient(data: Partial<AlertRecipient>): { valid: boolean; errors: string[] } {
        const errors: string[] = []

        if (!data.name || data.name.trim().length === 0) {
            errors.push('Name is required')
        }

        if (!data.phone && !data.email) {
            errors.push('At least one contact method (phone or email) is required')
        }

        if (data.phone) {
            const phoneValidation = this.twilioService.validatePhoneNumber(data.phone)
            if (!phoneValidation.valid) {
                errors.push(phoneValidation.error || 'Invalid phone number')
            }
        }

        if (data.email) {
            const emailValidation = this.sendGridService.validateEmail(data.email)
            if (!emailValidation.valid) {
                errors.push(emailValidation.error || 'Invalid email address')
            }
        }

        if (!data.preferredChannels || data.preferredChannels.length === 0) {
            errors.push('At least one preferred channel is required')
        }

        return {
            valid: errors.length === 0,
            errors,
        }
    }
}

// Singleton instance
let alertService: AlertService | null = null

export function getAlertService(): AlertService {
    if (!alertService) {
        alertService = new AlertService()
    }
    return alertService
}
