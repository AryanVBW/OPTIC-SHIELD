export interface Device {
  id: string
  name: string
  status: 'online' | 'offline' | 'error'
  lastSeen: string
  location: {
    name: string
    latitude: number
    longitude: number
  }
  stats: {
    uptime: number
    detectionCount: number
    cpuPercent: number
    memoryPercent: number
    temperature: number | null
  }
}

export interface Detection {
  id: number
  deviceId: string
  deviceName: string
  timestamp: string
  className: string
  confidence: number
  bbox: number[]
  imageUrl?: string
}

export interface DashboardStats {
  totalDevices: number
  onlineDevices: number
  totalDetections24h: number
  totalDetectionsWeek: number
  classDistribution: Record<string, number>
  hourlyDetections: Array<{
    hour: string
    count: number
  }>
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export interface HeartbeatPayload {
  device_id: string
  timestamp: number
  status: string
  stats: Record<string, unknown>
}

export interface DetectionPayload {
  detection_id: number
  device_id: string
  timestamp: number
  class_name: string
  confidence: number
  bbox: number[]
  image_base64?: string
}
