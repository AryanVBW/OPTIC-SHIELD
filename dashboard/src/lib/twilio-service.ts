import { Detection } from '@/types'

interface TwilioConfig {
    accountSid: string
    authToken: string
    whatsappNumber: string
    smsNumber: string
}

interface MessageResult {
    success: boolean
    messageId?: string
    error?: string
}

export class TwilioService {
    private config: TwilioConfig
    private twilio: any

    constructor() {
        this.config = {
            accountSid: process.env.TWILIO_ACCOUNT_SID || '',
            authToken: process.env.TWILIO_AUTH_TOKEN || '',
            whatsappNumber: process.env.TWILIO_WHATSAPP_NUMBER || 'whatsapp:+14155238886',
            smsNumber: process.env.TWILIO_SMS_NUMBER || '',
        }

        // Initialize Twilio client only if credentials are provided
        if (this.config.accountSid && this.config.authToken) {
            try {
                const twilio = require('twilio')
                this.twilio = twilio(this.config.accountSid, this.config.authToken)
            } catch (error) {
                console.error('Failed to initialize Twilio client:', error)
            }
        }
    }

    /**
     * Check if Twilio is properly configured
     */
    isConfigured(): boolean {
        return !!(this.config.accountSid && this.config.authToken && this.twilio)
    }

    /**
     * Send WhatsApp message with detection details
     */
    async sendWhatsAppAlert(
        to: string,
        detection: Detection,
        customMessage?: string
    ): Promise<MessageResult> {
        if (!this.isConfigured()) {
            return {
                success: false,
                error: 'Twilio is not configured. Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables.',
            }
        }

        try {
            // Format message content
            const message = this.formatDetectionMessage(detection, customMessage)

            // Ensure phone number is in E.164 format for WhatsApp
            const whatsappTo = to.startsWith('whatsapp:') ? to : `whatsapp:${to}`

            const messageOptions: any = {
                from: this.config.whatsappNumber,
                to: whatsappTo,
                body: message,
            }

            // Add image if available
            if (detection.imageUrl) {
                messageOptions.mediaUrl = [detection.imageUrl]
            }

            const result = await this.twilio.messages.create(messageOptions)

            return {
                success: true,
                messageId: result.sid,
            }
        } catch (error: any) {
            console.error('WhatsApp send error:', error)
            return {
                success: false,
                error: error.message || 'Failed to send WhatsApp message',
            }
        }
    }

    /**
     * Send SMS message with detection details
     */
    async sendSMSAlert(
        to: string,
        detection: Detection,
        customMessage?: string
    ): Promise<MessageResult> {
        if (!this.isConfigured()) {
            return {
                success: false,
                error: 'Twilio is not configured. Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables.',
            }
        }

        try {
            const message = this.formatDetectionMessage(detection, customMessage, true)

            const result = await this.twilio.messages.create({
                from: this.config.smsNumber,
                to: to,
                body: message,
            })

            return {
                success: true,
                messageId: result.sid,
            }
        } catch (error: any) {
            console.error('SMS send error:', error)
            return {
                success: false,
                error: error.message || 'Failed to send SMS',
            }
        }
    }

    /**
     * Format detection data into user-friendly message
     */
    private formatDetectionMessage(
        detection: Detection,
        customMessage?: string,
        isSMS: boolean = false
    ): string {
        const emoji = isSMS ? '' : '🚨 '
        const lines: string[] = []

        lines.push(`${emoji}WILDLIFE ALERT`)
        lines.push('')

        if (customMessage) {
            lines.push(customMessage)
            lines.push('')
        }

        lines.push(`Animal: ${detection.className}`)
        lines.push(`Confidence: ${(detection.confidence * 100).toFixed(1)}%`)
        lines.push(`Device: ${detection.deviceName}`)
        lines.push(`Time: ${new Date(detection.timestamp).toLocaleString()}`)

        if (detection.location) {
            lines.push('')
            lines.push(`Location: ${detection.location.name}`)
            lines.push(`GPS: ${detection.location.latitude.toFixed(6)}, ${detection.location.longitude.toFixed(6)}`)

            // Add Google Maps link
            const mapsUrl = `https://maps.google.com/?q=${detection.location.latitude},${detection.location.longitude}`
            lines.push(`Map: ${mapsUrl}`)
        }

        if (detection.metadata?.priority) {
            lines.push('')
            lines.push(`Priority: ${detection.metadata.priority.toUpperCase()}`)
        }

        if (!isSMS) {
            lines.push('')
            lines.push('OPTIC-SHIELD Wildlife Defense System')
        }

        return lines.join('\n')
    }

    /**
     * Validate phone number format
     */
    validatePhoneNumber(phoneNumber: string): { valid: boolean; formatted?: string; error?: string } {
        try {
            const { parsePhoneNumber } = require('libphonenumber-js')
            const parsed = parsePhoneNumber(phoneNumber)

            if (!parsed || !parsed.isValid()) {
                return {
                    valid: false,
                    error: 'Invalid phone number format',
                }
            }

            return {
                valid: true,
                formatted: parsed.format('E.164'),
            }
        } catch (error) {
            return {
                valid: false,
                error: 'Phone number validation failed',
            }
        }
    }

    /**
     * Send bulk WhatsApp messages
     */
    async sendBulkWhatsApp(
        recipients: string[],
        detection: Detection,
        customMessage?: string,
        onProgress?: (sent: number, total: number) => void
    ): Promise<{ success: number; failed: number; results: MessageResult[] }> {
        const results: MessageResult[] = []
        let success = 0
        let failed = 0

        for (let i = 0; i < recipients.length; i++) {
            const result = await this.sendWhatsAppAlert(recipients[i], detection, customMessage)
            results.push(result)

            if (result.success) {
                success++
            } else {
                failed++
            }

            if (onProgress) {
                onProgress(i + 1, recipients.length)
            }

            // Small delay to avoid rate limiting
            if (i < recipients.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 1000))
            }
        }

        return { success, failed, results }
    }

    /**
     * Send bulk SMS messages
     */
    async sendBulkSMS(
        recipients: string[],
        detection: Detection,
        customMessage?: string,
        onProgress?: (sent: number, total: number) => void
    ): Promise<{ success: number; failed: number; results: MessageResult[] }> {
        const results: MessageResult[] = []
        let success = 0
        let failed = 0

        for (let i = 0; i < recipients.length; i++) {
            const result = await this.sendSMSAlert(recipients[i], detection, customMessage)
            results.push(result)

            if (result.success) {
                success++
            } else {
                failed++
            }

            if (onProgress) {
                onProgress(i + 1, recipients.length)
            }

            // Small delay to avoid rate limiting
            if (i < recipients.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 1000))
            }
        }

        return { success, failed, results }
    }
}

// Singleton instance
let twilioService: TwilioService | null = null

export function getTwilioService(): TwilioService {
    if (!twilioService) {
        twilioService = new TwilioService()
    }
    return twilioService
}
