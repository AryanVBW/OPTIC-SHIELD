import { NextRequest, NextResponse } from 'next/server'
import { verifyRequest, getDeviceStore, getDetectionStore } from '@/lib/auth'
import { Detection } from '@/types'

const deviceStore = getDeviceStore()
const detectionStore = getDetectionStore()

export async function POST(request: NextRequest) {
  try {
    const authResult = verifyRequest(request)
    if (!authResult.valid) {
      return NextResponse.json(
        { success: false, error: 'Unauthorized' },
        { status: 401 }
      )
    }

    const body = await request.json()
    const { detection_id, device_id, timestamp, class_name, confidence, bbox, image_base64 } = body

    if (!device_id || !class_name) {
      return NextResponse.json(
        { success: false, error: 'Missing required fields' },
        { status: 400 }
      )
    }

    const device = deviceStore.get(device_id)
    const deviceName = device?.name || device_id

    const detection: Detection = {
      id: detection_id || Date.now(),
      deviceId: device_id,
      deviceName: deviceName,
      timestamp: new Date(timestamp * 1000).toISOString(),
      className: class_name,
      confidence: confidence,
      bbox: bbox || [],
      imageUrl: image_base64 ? `data:image/jpeg;base64,${image_base64}` : undefined
    }

    const detections = detectionStore.get('all') || []
    detections.unshift(detection)
    
    if (detections.length > 1000) {
      detections.splice(1000)
    }
    detectionStore.set('all', detections)

    if (device) {
      device.stats.detectionCount = (device.stats.detectionCount || 0) + 1
      device.lastSeen = new Date().toISOString()
      deviceStore.set(device_id, device)
    }

    console.log(`Detection received: ${class_name} from ${deviceName}`)

    return NextResponse.json({ 
      success: true, 
      message: 'Detection recorded',
      detection_id: detection.id
    })
  } catch (error) {
    console.error('Error recording detection:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to record detection' },
      { status: 500 }
    )
  }
}
