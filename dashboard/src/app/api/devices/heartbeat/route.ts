import { NextRequest, NextResponse } from 'next/server'
import { verifyRequest, getDeviceStore } from '@/lib/auth'

const deviceStore = getDeviceStore()

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
    const { device_id, timestamp, status, stats } = body

    if (!device_id) {
      return NextResponse.json(
        { success: false, error: 'Device ID required' },
        { status: 400 }
      )
    }

    const existingDevice = deviceStore.get(device_id)
    
    if (existingDevice) {
      existingDevice.lastSeen = new Date().toISOString()
      existingDevice.status = status === 'online' ? 'online' : 'offline'
      
      if (stats) {
        existingDevice.stats = {
          uptime: stats.uptime_seconds || 0,
          detectionCount: stats.detection_count || existingDevice.stats.detectionCount,
          cpuPercent: stats.system?.cpu_percent || 0,
          memoryPercent: stats.system?.memory_percent || 0,
          temperature: stats.system?.temperature_celsius || null
        }
      }
      
      deviceStore.set(device_id, existingDevice)
    }

    return NextResponse.json({ 
      success: true, 
      message: 'Heartbeat received',
      timestamp: Date.now()
    })
  } catch (error) {
    console.error('Error processing heartbeat:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to process heartbeat' },
      { status: 500 }
    )
  }
}
