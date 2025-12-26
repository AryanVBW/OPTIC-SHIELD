'use client'

import { useState, useEffect } from 'react'
import { Shield, Camera, AlertTriangle, Activity, Wifi, WifiOff } from 'lucide-react'
import DeviceCard from '@/components/DeviceCard'
import DetectionList from '@/components/DetectionList'
import StatsOverview from '@/components/StatsOverview'
import { Device, Detection, DashboardStats } from '@/types'

export default function Dashboard() {
  const [devices, setDevices] = useState<Device[]>([])
  const [detections, setDetections] = useState<Detection[]>([])
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDashboardData()
    const interval = setInterval(fetchDashboardData, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchDashboardData = async () => {
    try {
      const [devicesRes, detectionsRes, statsRes] = await Promise.all([
        fetch('/api/devices'),
        fetch('/api/detections?limit=20'),
        fetch('/api/stats')
      ])

      if (devicesRes.ok) {
        const devicesData = await devicesRes.json()
        setDevices(devicesData.devices || [])
      }

      if (detectionsRes.ok) {
        const detectionsData = await detectionsRes.json()
        setDetections(detectionsData.detections || [])
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json()
        setStats(statsData)
      }

      setError(null)
    } catch (err) {
      setError('Failed to fetch dashboard data')
      console.error('Dashboard fetch error:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <Shield className="w-16 h-16 text-green-500 animate-pulse mx-auto mb-4" />
          <p className="text-slate-400">Loading OPTIC-SHIELD Dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-green-500" />
            <div>
              <h1 className="text-xl font-bold">OPTIC-SHIELD</h1>
              <p className="text-sm text-slate-400">Wildlife Detection System</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              {devices.some(d => d.status === 'online') ? (
                <>
                  <Wifi className="w-4 h-4 text-green-500" />
                  <span className="text-green-500">
                    {devices.filter(d => d.status === 'online').length} Online
                  </span>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4 text-slate-500" />
                  <span className="text-slate-500">No devices online</span>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 bg-red-900/50 border border-red-700 rounded-lg p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <p className="text-red-200">{error}</p>
          </div>
        )}

        {/* Stats Overview */}
        <StatsOverview stats={stats} />

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
          {/* Devices Section */}
          <div className="lg:col-span-1">
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Camera className="w-5 h-5 text-blue-400" />
                <h2 className="text-lg font-semibold">Devices</h2>
                <span className="ml-auto text-sm text-slate-400">
                  {devices.length} total
                </span>
              </div>
              
              {devices.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <Camera className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No devices registered</p>
                  <p className="text-sm mt-1">Devices will appear here when connected</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {devices.map(device => (
                    <DeviceCard key={device.id} device={device} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Detections Section */}
          <div className="lg:col-span-2">
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-orange-400" />
                <h2 className="text-lg font-semibold">Recent Detections</h2>
                <span className="ml-auto text-sm text-slate-400">
                  Last 24 hours
                </span>
              </div>
              
              <DetectionList detections={detections} />
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
