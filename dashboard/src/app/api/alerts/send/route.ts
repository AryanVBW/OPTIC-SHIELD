import { NextRequest, NextResponse } from 'next/server'
import { getAlertService } from '@/lib/alert-service'
import { getDetectionStore } from '@/lib/auth'

const alertService = getAlertService()
const detectionStore = getDetectionStore()

/**
 * POST /api/alerts/send
 * Send bulk alerts to selected recipients
 */
export async function POST(request: NextRequest) {
    try {
        const body = await request.json()

        const { detectionIds, recipientIds, channels, customMessage } = body

        // Validate request
        if (!detectionIds || !Array.isArray(detectionIds) || detectionIds.length === 0) {
            return NextResponse.json(
                { success: false, error: 'Detection IDs are required' },
                { status: 400 }
            )
        }

        if (!recipientIds || !Array.isArray(recipientIds) || recipientIds.length === 0) {
            return NextResponse.json(
                { success: false, error: 'Recipient IDs are required' },
                { status: 400 }
            )
        }

        if (!channels || !Array.isArray(channels) || channels.length === 0) {
            return NextResponse.json(
                { success: false, error: 'At least one channel is required' },
                { status: 400 }
            )
        }

        // Get detections
        const allDetections = detectionStore.get('all') || []
        const detections = allDetections.filter(d => detectionIds.includes(d.id))

        if (detections.length === 0) {
            return NextResponse.json(
                { success: false, error: 'No valid detections found' },
                { status: 404 }
            )
        }

        // Check service availability
        const serviceStatus = alertService.getServiceStatus()
        const unavailableChannels = channels.filter(ch => {
            if (ch === 'whatsapp' || ch === 'sms') return !serviceStatus.whatsapp
            if (ch === 'email') return !serviceStatus.email
            return false
        })

        if (unavailableChannels.length > 0) {
            return NextResponse.json(
                {
                    success: false,
                    error: `The following channels are not configured: ${unavailableChannels.join(', ')}`,
                    serviceStatus,
                },
                { status: 503 }
            )
        }

        // Send bulk alerts
        const result = await alertService.sendBulkAlerts(
            {
                detectionIds,
                recipientIds,
                channels,
                customMessage,
            },
            detections
        )

        return NextResponse.json({
            success: true,
            messages: result.messages,
            summary: result.summary,
        })
    } catch (error: any) {
        console.error('Error sending bulk alerts:', error)
        return NextResponse.json(
            { success: false, error: error.message || 'Failed to send alerts' },
            { status: 500 }
        )
    }
}

/**
 * GET /api/alerts/send/status
 * Get service availability status
 */
export async function GET(request: NextRequest) {
    try {
        const serviceStatus = alertService.getServiceStatus()

        return NextResponse.json({
            success: true,
            status: serviceStatus,
            message: Object.values(serviceStatus).every(v => v)
                ? 'All services are configured'
                : 'Some services are not configured. Check environment variables.',
        })
    } catch (error: any) {
        console.error('Error checking service status:', error)
        return NextResponse.json(
            { success: false, error: error.message || 'Failed to check service status' },
            { status: 500 }
        )
    }
}
