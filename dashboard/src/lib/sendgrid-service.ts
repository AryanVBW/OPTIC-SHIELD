import { Detection } from '@/types'

interface SendGridConfig {
    apiKey: string
    fromEmail: string
    fromName: string
}

interface EmailResult {
    success: boolean
    messageId?: string
    error?: string
}

export class SendGridService {
    private config: SendGridConfig
    private sendgrid: any

    constructor() {
        this.config = {
            apiKey: process.env.SENDGRID_API_KEY || '',
            fromEmail: process.env.SENDGRID_FROM_EMAIL || 'alerts@optic-shield.com',
            fromName: process.env.SENDGRID_FROM_NAME || 'OPTIC-SHIELD Alerts',
        }

        // Initialize SendGrid client only if API key is provided
        if (this.config.apiKey) {
            try {
                const sgMail = require('@sendgrid/mail')
                sgMail.setApiKey(this.config.apiKey)
                this.sendgrid = sgMail
            } catch (error) {
                console.error('Failed to initialize SendGrid client:', error)
            }
        }
    }

    /**
     * Check if SendGrid is properly configured
     */
    isConfigured(): boolean {
        return !!(this.config.apiKey && this.sendgrid)
    }

    /**
     * Send email alert with detection details
     */
    async sendEmailAlert(
        to: string,
        detection: Detection,
        customMessage?: string
    ): Promise<EmailResult> {
        if (!this.isConfigured()) {
            return {
                success: false,
                error: 'SendGrid is not configured. Please set SENDGRID_API_KEY environment variable.',
            }
        }

        try {
            const subject = `🚨 Wildlife Alert: ${detection.className} Detected`
            const htmlContent = this.generateEmailHTML(detection, customMessage)
            const textContent = this.generateEmailText(detection, customMessage)

            const msg = {
                to: to,
                from: {
                    email: this.config.fromEmail,
                    name: this.config.fromName,
                },
                subject: subject,
                text: textContent,
                html: htmlContent,
            }

            const [response] = await this.sendgrid.send(msg)

            return {
                success: true,
                messageId: response.headers['x-message-id'],
            }
        } catch (error: any) {
            console.error('Email send error:', error)
            return {
                success: false,
                error: error.message || 'Failed to send email',
            }
        }
    }

    /**
     * Generate HTML email content
     */
    private generateEmailHTML(detection: Detection, customMessage?: string): string {
        const locationMap = detection.location
            ? `https://maps.google.com/?q=${detection.location.latitude},${detection.location.longitude}`
            : null

        return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Wildlife Alert</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
      background-color: #f5f5f5;
    }
    .container {
      background: white;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .header {
      background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
      color: white;
      padding: 30px 20px;
      text-align: center;
    }
    .header h1 {
      margin: 0;
      font-size: 24px;
      font-weight: bold;
    }
    .alert-icon {
      font-size: 48px;
      margin-bottom: 10px;
    }
    .content {
      padding: 30px 20px;
    }
    .detection-image {
      width: 100%;
      max-width: 560px;
      height: auto;
      border-radius: 8px;
      margin: 20px 0;
    }
    .details {
      background: #f9fafb;
      border-left: 4px solid #ef4444;
      padding: 15px;
      margin: 20px 0;
      border-radius: 4px;
    }
    .detail-row {
      display: flex;
      padding: 8px 0;
      border-bottom: 1px solid #e5e7eb;
    }
    .detail-row:last-child {
      border-bottom: none;
    }
    .detail-label {
      font-weight: 600;
      min-width: 120px;
      color: #6b7280;
    }
    .detail-value {
      color: #111827;
    }
    .priority-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
    }
    .priority-critical {
      background: #fee2e2;
      color: #dc2626;
    }
    .priority-high {
      background: #fed7aa;
      color: #ea580c;
    }
    .priority-medium {
      background: #fef3c7;
      color: #d97706;
    }
    .map-button {
      display: inline-block;
      background: #3b82f6;
      color: white;
      padding: 12px 24px;
      text-decoration: none;
      border-radius: 6px;
      margin: 20px 0;
      font-weight: 600;
    }
    .map-button:hover {
      background: #2563eb;
    }
    .footer {
      background: #f9fafb;
      padding: 20px;
      text-align: center;
      color: #6b7280;
      font-size: 14px;
      border-top: 1px solid #e5e7eb;
    }
    .custom-message {
      background: #dbeafe;
      border-left: 4px solid #3b82f6;
      padding: 15px;
      margin: 20px 0;
      border-radius: 4px;
      color: #1e40af;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="alert-icon">🚨</div>
      <h1>WILDLIFE ALERT</h1>
      <p style="margin: 5px 0 0 0; opacity: 0.9;">OPTIC-SHIELD Detection System</p>
    </div>

    <div class="content">
      ${customMessage ? `<div class="custom-message">${customMessage}</div>` : ''}

      ${detection.imageUrl ? `<img src="${detection.imageUrl}" alt="Detection Image" class="detection-image">` : ''}

      <div class="details">
        <div class="detail-row">
          <span class="detail-label">Animal</span>
          <span class="detail-value"><strong>${detection.className}</strong></span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Confidence</span>
          <span class="detail-value">${(detection.confidence * 100).toFixed(1)}%</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Device</span>
          <span class="detail-value">${detection.deviceName}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Time</span>
          <span class="detail-value">${new Date(detection.timestamp).toLocaleString()}</span>
        </div>
        ${detection.location ? `
        <div class="detail-row">
          <span class="detail-label">Location</span>
          <span class="detail-value">${detection.location.name}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Coordinates</span>
          <span class="detail-value">${detection.location.latitude.toFixed(6)}, ${detection.location.longitude.toFixed(6)}</span>
        </div>
        ` : ''}
        ${detection.metadata?.priority ? `
        <div class="detail-row">
          <span class="detail-label">Priority</span>
          <span class="detail-value">
            <span class="priority-badge priority-${detection.metadata.priority}">${detection.metadata.priority}</span>
          </span>
        </div>
        ` : ''}
      </div>

      ${locationMap ? `
      <div style="text-align: center;">
        <a href="${locationMap}" class="map-button" target="_blank">📍 View on Google Maps</a>
      </div>
      ` : ''}
    </div>

    <div class="footer">
      <p style="margin: 0;">
        This alert was generated by the <strong>OPTIC-SHIELD</strong> Wildlife Defense System.
      </p>
      <p style="margin: 10px 0 0 0; font-size: 12px;">
        Automated wildlife detection and monitoring system
      </p>
    </div>
  </div>
</body>
</html>
    `
    }

    /**
     * Generate plain text email content
     */
    private generateEmailText(detection: Detection, customMessage?: string): string {
        const lines: string[] = []

        lines.push('WILDLIFE ALERT')
        lines.push('=================')
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
            lines.push(`GPS Coordinates: ${detection.location.latitude.toFixed(6)}, ${detection.location.longitude.toFixed(6)}`)
            lines.push(`Map: https://maps.google.com/?q=${detection.location.latitude},${detection.location.longitude}`)
        }

        if (detection.metadata?.priority) {
            lines.push('')
            lines.push(`Priority: ${detection.metadata.priority.toUpperCase()}`)
        }

        lines.push('')
        lines.push('---')
        lines.push('OPTIC-SHIELD Wildlife Defense System')
        lines.push('Automated wildlife detection and monitoring')

        return lines.join('\n')
    }

    /**
     * Validate email address
     */
    validateEmail(email: string): { valid: boolean; error?: string } {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

        if (!emailRegex.test(email)) {
            return {
                valid: false,
                error: 'Invalid email address format',
            }
        }

        return { valid: true }
    }

    /**
     * Send bulk emails
     */
    async sendBulkEmails(
        recipients: string[],
        detection: Detection,
        customMessage?: string,
        onProgress?: (sent: number, total: number) => void
    ): Promise<{ success: number; failed: number; results: EmailResult[] }> {
        const results: EmailResult[] = []
        let success = 0
        let failed = 0

        for (let i = 0; i < recipients.length; i++) {
            const result = await this.sendEmailAlert(recipients[i], detection, customMessage)
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
                await new Promise(resolve => setTimeout(resolve, 500))
            }
        }

        return { success, failed, results }
    }
}

// Singleton instance
let sendGridService: SendGridService | null = null

export function getSendGridService(): SendGridService {
    if (!sendGridService) {
        sendGridService = new SendGridService()
    }
    return sendGridService
}
