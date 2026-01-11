import { NextRequest, NextResponse } from 'next/server'
import { getAlertService } from '@/lib/alert-service'

const alertService = getAlertService()

/**
 * GET /api/alerts/history
 * Get alert sending history
 */
export async function GET(request: NextRequest) {
    try {
        const { searchParams } = new URL(request.url)
        const limit = searchParams.get('limit') ? parseInt(searchParams.get('limit')!) : undefined
        const recipientId = searchParams.get('recipient_id')

        let history
        if (recipientId) {
            history = alertService.getRecipientAlertHistory(recipientId, limit)
        } else {
            history = alertService.getAlertHistory(limit)
        }

        // Get statistics
        const stats = alertService.getAlertStats()

        return NextResponse.json({
            success: true,
            history,
            stats,
            count: history.length,
        })
    } catch (error: any) {
        console.error('Error fetching alert history:', error)
        return NextResponse.json(
            { success: false, error: error.message || 'Failed to fetch alert history' },
            { status: 500 }
        )
    }
}
