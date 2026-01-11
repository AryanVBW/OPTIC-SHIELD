export interface CameraInfo {
  id: string
  name: string
  model: string
  resolution: string
  status: 'active' | 'inactive' | 'error'
}

export interface DeviceLocation {
  name: string
  latitude: number
  longitude: number
  altitude?: number
  timezone?: string
}

export interface DeviceStats {
  uptime: number
  detectionCount: number
  cpuPercent: number
  memoryPercent: number
  memoryUsedMb: number
  memoryTotalMb: number
  temperature: number | null
  temperatureUnit: 'celsius' | 'fahrenheit'
  storageUsedGb: number
  storageTotalGb: number
  storagePercent: number
  powerConsumptionWatts: number | null
  powerSource: 'battery' | 'ac' | 'solar' | 'unknown'
  batteryPercent: number | null
  networkLatencyMs: number | null
  lastHeartbeat: string
}

export interface Device {
  id: string
  name: string
  status: 'online' | 'offline' | 'error' | 'maintenance'
  lastSeen: string
  location: DeviceLocation
  stats: DeviceStats
  cameras: CameraInfo[]
  cameraCount: number
  firmwareVersion: string
  hardwareModel: string
  environment: 'production' | 'development' | 'staging'
  tags: string[]
}

export interface DetectionLocation {
  name: string
  latitude: number
  longitude: number
}

export interface Detection {
  id: number
  eventId?: string
  deviceId: string
  deviceName: string
  cameraId?: string
  timestamp: string
  className: string
  confidence: number
  bbox: number[]
  imageUrl?: string
  location?: DetectionLocation
  metadata?: {
    processingTimeMs?: number
    priority?: string
    frameTimestamp?: number
    deviceInfo?: Record<string, any>
    uploadTimestamp?: number
  }
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
  stats: {
    uptime_seconds: number
    detection_count: number
    system: {
      cpu_percent: number
      memory_percent: number
      memory_used_mb: number
      memory_total_mb: number
      temperature_celsius: number | null
      disk_percent: number
      disk_used_gb: number
      disk_total_gb: number
    }
    power?: {
      consumption_watts: number | null
      source: 'battery' | 'ac' | 'solar' | 'unknown'
      battery_percent: number | null
    }
    cameras?: Array<{
      id: string
      name: string
      model: string
      resolution: string
      status: 'active' | 'inactive' | 'error'
    }>
    network?: {
      latency_ms: number | null
    }
  }
}

export interface DeviceTelemetry {
  deviceId: string
  timestamp: string
  cpu: number
  memory: number
  temperature: number | null
  storage: number
  power: number | null
  status: 'online' | 'offline' | 'error'
}

export interface DetectionPayload {
  event_id?: string
  detection_id: number
  device_id: string
  camera_id?: string
  timestamp: number
  class_name: string
  class_id?: number
  confidence: number
  bbox: number[]
  image_base64?: string
  location?: {
    name: string
    latitude: number
    longitude: number
  }
  metadata?: {
    processing_time_ms?: number
    priority?: string
    frame_timestamp?: number
    device_info?: Record<string, any>
    upload_timestamp?: number
  }
}

// Alert System Types
export interface AlertRecipient {
  id: string
  name: string
  phone?: string  // E.164 format for WhatsApp/SMS
  email?: string
  preferredChannels: ('whatsapp' | 'sms' | 'email')[]
  active: boolean
  createdAt: string
}

export interface AlertMessage {
  id: string
  detectionId: number
  recipientId: string
  recipientName: string
  channel: 'whatsapp' | 'sms' | 'email'
  status: 'pending' | 'sent' | 'failed' | 'delivered'
  sentAt?: string
  deliveredAt?: string
  error?: string
}

export interface BulkAlertRequest {
  detectionIds: number[]
  recipientIds: string[]
  channels: ('whatsapp' | 'sms' | 'email')[]
  customMessage?: string
}

export interface AlertStats {
  totalSent: number
  totalFailed: number
  byChannel: Record<string, { sent: number; failed: number }>
  recentAlerts: AlertMessage[]
}
