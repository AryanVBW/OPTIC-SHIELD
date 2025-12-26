'use client'

import { AlertCircle } from 'lucide-react'
import { Detection } from '@/types'
import { format } from 'date-fns'

interface DetectionListProps {
  detections: Detection[]
}

const animalEmojis: Record<string, string> = {
  bird: '🐦',
  cat: '🐱',
  dog: '🐕',
  horse: '🐴',
  sheep: '🐑',
  cow: '🐄',
  elephant: '🐘',
  bear: '🐻',
  zebra: '🦓',
  giraffe: '🦒',
  default: '🦁'
}

export default function DetectionList({ detections }: DetectionListProps) {
  if (detections.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>No detections yet</p>
        <p className="text-sm mt-1">Wildlife detections will appear here</p>
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-[500px] overflow-y-auto">
      {detections.map((detection) => (
        <div
          key={`${detection.deviceId}-${detection.id}`}
          className="flex items-center gap-4 p-3 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors"
        >
          <div className="text-3xl">
            {animalEmojis[detection.className.toLowerCase()] || animalEmojis.default}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-white capitalize">
                {detection.className}
              </span>
              <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded-full">
                {(detection.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="text-sm text-slate-400 truncate">
              {detection.deviceName}
            </div>
          </div>

          <div className="text-right text-sm text-slate-500">
            <div>{format(new Date(detection.timestamp), 'HH:mm')}</div>
            <div>{format(new Date(detection.timestamp), 'MMM d')}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
