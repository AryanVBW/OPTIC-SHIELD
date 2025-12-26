import { NextRequest } from 'next/server'
import { Device, Detection } from '@/types'

const API_SECRET_KEY = process.env.API_SECRET_KEY || 'development-key'

const deviceStore = new Map<string, Device>()
const detectionStore = new Map<string, Detection[]>()

export function getDeviceStore(): Map<string, Device> {
  return deviceStore
}

export function getDetectionStore(): Map<string, Detection[]> {
  return detectionStore
}

export interface AuthResult {
  valid: boolean
  deviceId?: string
  error?: string
}

export function verifyRequest(request: NextRequest): AuthResult {
  const apiKey = request.headers.get('X-API-Key')
  const deviceId = request.headers.get('X-Device-ID')
  const timestamp = request.headers.get('X-Timestamp')
  const signature = request.headers.get('X-Signature')

  if (!apiKey) {
    return { valid: false, error: 'Missing API key' }
  }

  if (apiKey !== API_SECRET_KEY) {
    return { valid: false, error: 'Invalid API key' }
  }

  if (!deviceId) {
    return { valid: false, error: 'Missing device ID' }
  }

  if (timestamp) {
    const requestTime = parseInt(timestamp)
    const now = Math.floor(Date.now() / 1000)
    const timeDiff = Math.abs(now - requestTime)
    
    if (timeDiff > 300) {
      return { valid: false, error: 'Request timestamp too old' }
    }
  }

  return { valid: true, deviceId }
}

export function generateApiKey(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < 32; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}
