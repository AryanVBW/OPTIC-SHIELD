'use client'

import { Wifi, WifiOff, Thermometer, Cpu, HardDrive } from 'lucide-react'
import { Device } from '@/types'
import { formatDistanceToNow } from 'date-fns'

interface DeviceCardProps {
  device: Device
}

export default function DeviceCard({ device }: DeviceCardProps) {
  const isOnline = device.status === 'online'
  const lastSeenText = formatDistanceToNow(new Date(device.lastSeen), { addSuffix: true })

  return (
    <div className={`
      p-4 rounded-lg border transition-all
      ${isOnline
        ? 'bg-emerald-500/10 border-emerald-500/20 dark:bg-green-900/20 dark:border-green-700/50'
        : 'bg-surface/50 border-border dark:bg-slate-700/30 dark:border-slate-600/50'
      }
    `}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-medium text-foreground">{device.name}</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">{device.location.name}</p>
        </div>
        <div className={`
          flex items-center gap-1 px-2 py-1 rounded-full text-xs
          ${isOnline
            ? 'bg-emerald-100 text-emerald-700 dark:bg-green-500/20 dark:text-green-400'
            : 'bg-slate-100 text-slate-500 dark:bg-slate-600/50 dark:text-slate-400'
          }
        `}>
          {isOnline ? (
            <Wifi className="w-3 h-3" />
          ) : (
            <WifiOff className="w-3 h-3" />
          )}
          {isOnline ? 'Online' : 'Offline'}
        </div>
      </div>

      {isOnline && device.stats && (
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="flex items-center gap-1 text-slate-400">
            <Cpu className="w-3 h-3" />
            <span>{device.stats.cpuPercent}%</span>
          </div>
          <div className="flex items-center gap-1 text-slate-400">
            <HardDrive className="w-3 h-3" />
            <span>{device.stats.memoryPercent}%</span>
          </div>
          {device.stats.temperature && (
            <div className="flex items-center gap-1 text-slate-400">
              <Thermometer className="w-3 h-3" />
              <span>{device.stats.temperature}°C</span>
            </div>
          )}
        </div>
      )}

      <div className="mt-3 pt-3 border-t border-border dark:border-slate-600/50 flex justify-between text-xs text-slate-500">
        <span>{device.stats?.detectionCount || 0} detections</span>
        <span>{lastSeenText}</span>
      </div>
    </div>
  )
}
