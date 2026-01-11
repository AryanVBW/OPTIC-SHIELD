import { NextRequest, NextResponse } from 'next/server'
import { getAlertService } from '@/lib/alert-service'

const alertService = getAlertService()

/**
 * GET /api/alerts/recipients
 * Get all alert recipients
 */
export async function GET(request: NextRequest) {
    try {
        const recipients = alertService.getAllRecipients()

        return NextResponse.json({
            success: true,
            recipients,
            count: recipients.length,
        })
    } catch (error) {
        console.error('Error fetching recipients:', error)
        return NextResponse.json(
            { success: false, error: 'Failed to fetch recipients' },
            { status: 500 }
        )
    }
}

/**
 * POST /api/alerts/recipients
 * Add a new alert recipient
 */
export async function POST(request: NextRequest) {
    try {
        const body = await request.json()

        // Validate recipient data
        const validation = alertService.validateRecipient(body)
        if (!validation.valid) {
            return NextResponse.json(
                {
                    success: false,
                    error: 'Validation failed',
                    errors: validation.errors,
                },
                { status: 400 }
            )
        }

        const recipient = alertService.addRecipient({
            name: body.name,
            phone: body.phone,
            email: body.email,
            preferredChannels: body.preferredChannels || [],
            active: body.active !== undefined ? body.active : true,
        })

        return NextResponse.json({
            success: true,
            recipient,
        })
    } catch (error: any) {
        console.error('Error adding recipient:', error)
        return NextResponse.json(
            { success: false, error: error.message || 'Failed to add recipient' },
            { status: 500 }
        )
    }
}

/**
 * PUT /api/alerts/recipients
 * Update an existing recipient
 */
export async function PUT(request: NextRequest) {
    try {
        const body = await request.json()
        const { id, ...updates } = body

        if (!id) {
            return NextResponse.json(
                { success: false, error: 'Recipient ID is required' },
                { status: 400 }
            )
        }

        // Validate updates
        const validation = alertService.validateRecipient(updates)
        if (!validation.valid) {
            return NextResponse.json(
                {
                    success: false,
                    error: 'Validation failed',
                    errors: validation.errors,
                },
                { status: 400 }
            )
        }

        const recipient = alertService.updateRecipient(id, updates)

        if (!recipient) {
            return NextResponse.json(
                { success: false, error: 'Recipient not found' },
                { status: 404 }
            )
        }

        return NextResponse.json({
            success: true,
            recipient,
        })
    } catch (error: any) {
        console.error('Error updating recipient:', error)
        return NextResponse.json(
            { success: false, error: error.message || 'Failed to update recipient' },
            { status: 500 }
        )
    }
}

/**
 * DELETE /api/alerts/recipients
 * Delete a recipient
 */
export async function DELETE(request: NextRequest) {
    try {
        const { searchParams } = new URL(request.url)
        const id = searchParams.get('id')

        if (!id) {
            return NextResponse.json(
                { success: false, error: 'Recipient ID is required' },
                { status: 400 }
            )
        }

        const deleted = alertService.deleteRecipient(id)

        if (!deleted) {
            return NextResponse.json(
                { success: false, error: 'Recipient not found' },
                { status: 404 }
            )
        }

        return NextResponse.json({
            success: true,
            message: 'Recipient deleted successfully',
        })
    } catch (error: any) {
        console.error('Error deleting recipient:', error)
        return NextResponse.json(
            { success: false, error: error.message || 'Failed to delete recipient' },
            { status: 500 }
        )
    }
}
