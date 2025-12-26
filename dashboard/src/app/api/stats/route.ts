import { NextResponse } from 'next/server'
import { getDeviceStore, getDetectionStore } from '@/lib/auth'
import { DashboardStats, Detection, Device } from '@/types'

const deviceStore = getDeviceStore()
const detectionStore = getDetectionStore()

export async function GET() {
  try {
    const devices = Array.from(deviceStore.values()) as Device[]
    const detections: Detection[] = detectionStore.get('all') || []

    const now = Date.now()
    const oneDayAgo = now - 24 * 60 * 60 * 1000
    const oneWeekAgo = now - 7 * 24 * 60 * 60 * 1000

    const onlineDevices = devices.filter(d => 
      (now - new Date(d.lastSeen).getTime()) < 120000
    ).length

    const detections24h = detections.filter(d => 
      new Date(d.timestamp).getTime() > oneDayAgo
    )

    const detectionsWeek = detections.filter(d => 
      new Date(d.timestamp).getTime() > oneWeekAgo
    )

    const classDistribution: Record<string, number> = {}
    for (const d of detections24h) {
      classDistribution[d.className] = (classDistribution[d.className] || 0) + 1
    }

    const sortedDistribution = Object.fromEntries(
      Object.entries(classDistribution).sort(([, a], [, b]) => b - a)
    )

    const hourlyDetections: Array<{ hour: string; count: number }> = []
    for (let i = 23; i >= 0; i--) {
      const hourStart = now - (i + 1) * 60 * 60 * 1000
      const hourEnd = now - i * 60 * 60 * 1000
      const count = detections.filter(d => {
        const t = new Date(d.timestamp).getTime()
        return t >= hourStart && t < hourEnd
      }).length
      
      const hour = new Date(hourEnd).getHours()
      hourlyDetections.push({
        hour: `${hour}:00`,
        count
      })
    }

    const stats: DashboardStats = {
      totalDevices: devices.length,
      onlineDevices,
      totalDetections24h: detections24h.length,
      totalDetectionsWeek: detectionsWeek.length,
      classDistribution: sortedDistribution,
      hourlyDetections
    }

    return NextResponse.json(stats)
  } catch (error) {
    console.error('Error fetching stats:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch stats' },
      { status: 500 }
    )
  }
}
