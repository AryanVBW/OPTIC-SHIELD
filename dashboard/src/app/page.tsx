'use client'

import { useState, useEffect, useCallback } from 'react'
import { Shield, Camera, Activity, BarChart3, Settings, RefreshCw, Zap, Wifi, WifiOff, ArrowRight } from 'lucide-react'
import Link from 'next/link'
import { Device, Detection, DashboardStats } from '@/types'
import { apiClient } from '@/lib/api-client'
import { useDeviceStream } from '@/lib/useDeviceStream'
import { EnhancedStatsOverview } from '@/components/EnhancedStatsOverview'
import { EnhancedDeviceCard } from '@/components/EnhancedDeviceCard'
import { EnhancedDetectionList } from '@/components/EnhancedDetectionList'
import { ActivityChart } from '@/components/ActivityChart'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Sidebar } from '@/components/layout/Sidebar'
import { SystemHealth } from '@/components/dashboard/SystemHealth'
import { RecentActivitySummary } from '@/components/dashboard/RecentActivitySummary'

export default function Dashboard() {
  const [detections, setDetections] = useState<Detection[]>([])
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  const {
    devices: streamDevices,
    isConnected: isStreamConnected,
    lastUpdate: streamLastUpdate
  } = useDeviceStream({
    onDeviceUpdate: useCallback((device: Device) => {
      setLastUpdate(new Date())
    }, [])
  })

  const [devices, setDevices] = useState<Device[]>([])

  useEffect(() => {
    if (streamDevices.length > 0) {
      setDevices(streamDevices)
      setLastUpdate(streamLastUpdate)
    }
  }, [streamDevices, streamLastUpdate])

  useEffect(() => {
    fetchDashboardData()
    const interval = setInterval(() => fetchDashboardData(), 15000)
    return () => clearInterval(interval)
  }, [])

  const fetchDashboardData = async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true)

    try {
      const [devicesData, detectionsData, statsData] = await Promise.all([
        apiClient.get<{ devices: Device[] }>('/api/devices'),
        apiClient.get<{ detections: Detection[] }>('/api/detections?limit=50'),
        apiClient.get<DashboardStats>('/api/stats')
      ])

      // Only use API devices if stream is not connected or has no devices
      if (!isStreamConnected || streamDevices.length === 0) {
        setDevices(devicesData.devices || [])
      }
      setDetections(detectionsData.detections || [])
      setStats(statsData)
      setError(null)
      setLastUpdate(new Date())
    } catch (err) {
      console.error('Dashboard fetch error:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const handleRefresh = () => {
    fetchDashboardData(true)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background relative overflow-hidden">
        {/* Background glow effects */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-500/10 rounded-full blur-3xl animate-pulse-slow animation-delay-500"></div>

        <div className="text-center relative z-10 p-8 glass-panel rounded-2xl border border-slate-800/50">
          <div className="relative mb-8">
            <div className="absolute inset-0 bg-primary-500/20 blur-xl rounded-full"></div>
            <Shield className="w-20 h-20 text-primary-500 mx-auto relative z-10" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-24 h-24 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
            </div>
          </div>
          <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">OPTIC-SHIELD</h2>
          <div className="flex items-center justify-center gap-2 text-slate-400">
            <LoadingSpinner label="Initializing System..." size="sm" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background/80 text-foreground flex font-sans transition-colors duration-300">
      <Sidebar onRefresh={handleRefresh} isRefreshing={refreshing} />

      {/* Main Content */}
      <main className="flex-1 overflow-auto relative p-4 md:p-6 space-y-6">

        {/* Row 1: System Health & Welcome */}
        <div className="space-y-6">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-foreground tracking-tight mb-1">
                System Overview
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Operational Metrics & Threat Monitoring
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link href="/live-feed">
                <Button variant="outline" size="sm" className="hidden md:flex border-border bg-surface/50 text-slate-600 dark:text-slate-300 hover:text-foreground">
                  Open Console
                </Button>
              </Link>
            </div>
          </div>

          {error && (
            <Alert variant="error" title="System Error" onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <SystemHealth devices={devices} onRefresh={handleRefresh} isRefreshing={refreshing} />
        </div>

        {/* Row 2: Key Stats */}
        <EnhancedStatsOverview stats={stats} />

        {/* Row 3: Activity & Monitoring */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[500px]">
          {/* Left: Activity Chart (2/3 width) */}
          <div className="lg:col-span-2 h-full">
            <Card variant="glass" className="h-full border-border shadow-xl shadow-black/5 dark:shadow-black/20 overflow-hidden">
              <CardHeader className="border-b border-border py-3 min-h-[60px]">
                <CardTitle icon={<BarChart3 className="w-4 h-4 text-primary-400" />}>
                  Detection Activity
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 h-[calc(100%-60px)]">
                <ActivityChart stats={stats} />
              </CardContent>
            </Card>
          </div>

          {/* Right: Recent Activity Feed (1/3 width) */}
          <div className="lg:col-span-1 h-full">
            <RecentActivitySummary detections={detections} />
          </div>
        </div>

      </main>
    </div>
  )
}
