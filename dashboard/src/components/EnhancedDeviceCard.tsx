'use client'

import { useRouter } from 'next/navigation'
import { Cpu, HardDrive, Thermometer, MapPin, Clock, Activity, ChevronRight } from 'lucide-react'
import { Device } from '@/types'
import { formatDistanceToNow } from 'date-fns'
import { Card, CardContent } from './ui/Card'
import { StatusIndicator } from './ui/StatusIndicator'

interface EnhancedDeviceCardProps {
  device: Device
  onClick?: () => void
}

export function EnhancedDeviceCard({ device, onClick }: EnhancedDeviceCardProps) {
  const router = useRouter()

  const handleClick = () => {
    if (onClick) {
      onClick()
    } else {
      router.push(`/devices/${device.id}`)
    }
  }
  const isOnline = device.status === 'online'
  const lastSeenText = formatDistanceToNow(new Date(device.lastSeen), { addSuffix: true })

  const getStatusType = () => {
    if (device.status === 'online') return 'online'
    if (device.status === 'error') return 'error'
    return 'offline'
  }

  return (
    <Card
      hover
      gradient
      variant="glass"
      className={`cursor-pointer transition-all duration-300 group ${isOnline ? 'border-emerald-500/30' : 'border-border dark:border-slate-800'
        }`}
      onClick={handleClick}
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${isOnline ? 'from-emerald-500/5 to-transparent' : 'from-slate-500/5 to-transparent'
        } opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />

      <CardContent className="p-5 relative">
        <div className="flex items-start justify-between mb-5">
          <div className="flex-1 min-w-0 pr-4">
            <h3 className="font-bold text-foreground text-lg mb-1 truncate tracking-tight group-hover:text-emerald-500 dark:group-hover:text-emerald-400 transition-colors">
              {device.name}
            </h3>
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400 bg-surface-highlight dark:bg-slate-800/50 w-fit px-2 py-1 rounded-md border border-border dark:border-slate-700/50">
              <MapPin className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">{device.location.name}</span>
            </div>
          </div>
          <StatusIndicator status={getStatusType()} showPulse={isOnline} />
        </div>

        {isOnline && device.stats ? (
          <div className="space-y-3 mb-5">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-surface/50 dark:bg-slate-950/40 rounded-lg p-3 border border-border dark:border-slate-800 group-hover:border-slate-300 dark:group-hover:border-slate-700/50 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <div className="p-1.5 rounded-md bg-blue-500/10">
                    <Cpu className="w-3.5 h-3.5 text-blue-400" />
                  </div>
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400">CPU</span>
                </div>
                <div className="text-lg font-bold text-foreground tracking-tight">
                  {device.stats.cpuPercent}%
                  <div className="w-full bg-slate-200 dark:bg-slate-800 h-1 mt-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-blue-500 h-full rounded-full transition-all duration-1000"
                      style={{ width: `${device.stats.cpuPercent}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="bg-surface/50 dark:bg-slate-950/40 rounded-lg p-3 border border-border dark:border-slate-800 group-hover:border-slate-300 dark:group-hover:border-slate-700/50 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <div className="p-1.5 rounded-md bg-violet-500/10">
                    <HardDrive className="w-3.5 h-3.5 text-violet-400" />
                  </div>
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Memory</span>
                </div>
                <div className="text-lg font-bold text-foreground tracking-tight">
                  {device.stats.memoryPercent}%
                  <div className="w-full bg-slate-200 dark:bg-slate-800 h-1 mt-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-violet-500 h-full rounded-full transition-all duration-1000"
                      style={{ width: `${device.stats.memoryPercent}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {device.stats.temperature !== null && (
              <div className="bg-surface/50 dark:bg-slate-950/40 rounded-lg p-3 border border-border dark:border-slate-800 group-hover:border-slate-300 dark:group-hover:border-slate-700/50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-amber-500/10">
                      <Thermometer className="w-3.5 h-3.5 text-amber-400" />
                    </div>
                    <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Temperature</span>
                  </div>
                  <div className="text-lg font-bold text-foreground tracking-tight">
                    {device.stats.temperature}°C
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center bg-slate-100 dark:bg-slate-900/20 rounded-lg border border-border dark:border-slate-800/50 border-dashed mb-5">
            <span className="text-sm text-slate-500 font-medium">Device Offline</span>
          </div>
        )}

        <div className="flex items-center justify-between pt-4 border-t border-slate-800/50">
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-full ${isOnline ? 'bg-emerald-500/10' : 'bg-slate-100 dark:bg-slate-800'}`}>
              <Activity className={`w-3.5 h-3.5 ${isOnline ? 'text-emerald-500 dark:text-emerald-400' : 'text-slate-500'}`} />
            </div>
            <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
              {device.stats?.detectionCount || 0} <span className="text-xs text-slate-400 dark:text-slate-500">detections</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
              <Clock className="w-3.5 h-3.5" />
              <span>{lastSeenText}</span>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 group-hover:translate-x-0.5 transition-all" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
