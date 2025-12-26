import { NextRequest, NextResponse } from 'next/server'
import { verifyRequest, getDeviceStore } from '@/lib/auth'
import { Device } from '@/types'

const deviceStore = getDeviceStore()

export async function GET(request: NextRequest) {
  try {
    const devices = Array.from(deviceStore.values())
    
    const now = Date.now()
    const devicesWithStatus = devices.map(device => ({
      ...device,
      status: (now - new Date(device.lastSeen).getTime()) < 120000 ? 'online' : 'offline'
    }))

    return NextResponse.json({ 
      success: true, 
      devices: devicesWithStatus 
    })
  } catch (error) {
    console.error('Error fetching devices:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch devices' },
      { status: 500 }
    )
  }
}

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
    const { device_id, info } = body

    if (!device_id) {
      return NextResponse.json(
        { success: false, error: 'Device ID required' },
        { status: 400 }
      )
    }

    const device: Device = {
      id: device_id,
      name: info?.name || device_id,
      status: 'online',
      lastSeen: new Date().toISOString(),
      location: {
        name: info?.location?.name || 'Unknown',
        latitude: info?.location?.latitude || 0,
        longitude: info?.location?.longitude || 0
      },
      stats: {
        uptime: 0,
        detectionCount: 0,
        cpuPercent: 0,
        memoryPercent: 0,
        temperature: null
      }
    }

    deviceStore.set(device_id, device)

    return NextResponse.json({ 
      success: true, 
      message: 'Device registered',
      device 
    })
  } catch (error) {
    console.error('Error registering device:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to register device' },
      { status: 500 }
    )
  }
}
