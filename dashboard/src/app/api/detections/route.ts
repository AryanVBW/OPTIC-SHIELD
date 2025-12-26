import { NextRequest, NextResponse } from 'next/server'
import { getDetectionStore } from '@/lib/auth'
import { Detection } from '@/types'

const detectionStore = getDetectionStore()

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '50')
    const deviceId = searchParams.get('device_id')

    let detections: Detection[] = detectionStore.get('all') || []

    if (deviceId) {
      detections = detections.filter(d => d.deviceId === deviceId)
    }

    detections = detections.slice(0, limit)

    return NextResponse.json({ 
      success: true, 
      detections,
      count: detections.length
    })
  } catch (error) {
    console.error('Error fetching detections:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch detections' },
      { status: 500 }
    )
  }
}
