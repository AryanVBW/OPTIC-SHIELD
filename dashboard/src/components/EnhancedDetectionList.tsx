'use client'

import { useState } from 'react'
import { AlertCircle, Filter, Search, Calendar, ChevronRight, MapPin, Camera, Clock, X, Image as ImageIcon, Zap } from 'lucide-react'
import { Detection } from '@/types'
import { format } from 'date-fns'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { Card } from './ui/Card'

interface EnhancedDetectionListProps {
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
  tiger: '🐅',
  lion: '🦁',
  leopard: '🐆',
  wolf: '🐺',
  deer: '🦌',
  default: '🦁'
}

export function EnhancedDetectionList({ detections }: EnhancedDetectionListProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedClass, setSelectedClass] = useState<string | null>(null)
  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null)

  const filteredDetections = detections.filter(detection => {
    const matchesSearch = detection.className.toLowerCase().includes(searchTerm.toLowerCase()) ||
      detection.deviceName.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesClass = !selectedClass || detection.className === selectedClass
    return matchesSearch && matchesClass
  })

  const uniqueClasses = Array.from(new Set(detections.map(d => d.className)))

  if (detections.length === 0) {
    return (
      <Card className="flex flex-col items-center justify-center py-20 bg-surface/20 dark:bg-slate-900/20 border-dashed border-border dark:border-slate-800">
        <div className="relative group">
          <div className="absolute inset-0 bg-emerald-500/20 blur-2xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
          <AlertCircle className="w-16 h-16 text-slate-400 dark:text-slate-600 mb-4 relative z-10" />
        </div>
        <p className="text-xl font-semibold text-foreground mb-2">No detections yet</p>
        <p className="text-sm text-slate-500 max-w-sm text-center">
          Wildlife detections will appear here automatically when your devices capture activity.
        </p>
      </Card>
    )
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'success'
    if (confidence >= 0.7) return 'info'
    if (confidence >= 0.5) return 'warning'
    return 'default'
  }

  return (
    <div className="space-y-6">
      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1 group">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-emerald-500 transition-colors" />
          <input
            type="text"
            placeholder="Search by animal or device..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-surface dark:bg-slate-900/50 border border-border dark:border-slate-700/50 rounded-xl text-foreground placeholder-slate-400 focus:outline-none focus:border-emerald-500/50 focus:bg-surface-highlight dark:focus:bg-slate-900/80 focus:ring-1 focus:ring-emerald-500/20 transition-all shadow-sm"
          />
        </div>

        <div className="flex gap-2 overflow-x-auto pb-2 sm:pb-0 scrollbar-none">
          <Button
            variant={selectedClass === null ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setSelectedClass(null)}
            className={`rounded-lg ${selectedClass === null ? 'shadow-lg shadow-emerald-500/20' : ''}`}
          >
            All
          </Button>
          {uniqueClasses.slice(0, 5).map(className => (
            <Button
              key={className}
              variant={selectedClass === className ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setSelectedClass(className)}
              className={`rounded-lg capitalize ${selectedClass === className ? 'shadow-lg shadow-emerald-500/20' : ''}`}
            >
              {className}
            </Button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
        {filteredDetections.map((detection) => (
          <div
            key={`${detection.deviceId}-${detection.id}`}
            onClick={() => setSelectedDetection(detection)}
            className="group relative flex items-center gap-5 p-4 spotlight-card glass-panel rounded-xl cursor-pointer transition-all duration-300 hover:border-nexus-accent/30"
          >
            {/* Hover Glint */}
            <div className="absolute top-0 left-0 w-[200%] h-full bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:animate-shimmer pointer-events-none" />

            {/* Image Thumbnail */}
            {detection.imageUrl ? (
              <div className="relative flex-shrink-0 w-14 h-14 rounded-xl overflow-hidden border border-slate-700/50 group-hover:border-emerald-500/30 transition-colors">
                <img
                  src={detection.imageUrl}
                  alt={detection.className}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
                <ImageIcon className="absolute bottom-1 right-1 w-3 h-3 text-white/70" />
              </div>
            ) : (
              <div className="relative flex-shrink-0 w-14 h-14 flex items-center justify-center bg-slate-800/50 rounded-xl border border-slate-700/50 group-hover:border-emerald-500/30 group-hover:bg-emerald-500/10 transition-colors">
                <span className="text-2xl transform group-hover:scale-110 transition-transform duration-300">
                  {animalEmojis[detection.className.toLowerCase()] || animalEmojis.default}
                </span>
              </div>
            )}

            <div className="flex-1 min-w-0 z-10">
              <div className="flex items-center gap-3 mb-1">
                <span className="font-bold text-foreground capitalize text-lg tracking-tight group-hover:text-emerald-500 dark:group-hover:text-emerald-400 transition-colors">
                  {detection.className}
                </span>
                <Badge
                  variant={getConfidenceColor(detection.confidence)}
                  size="sm"
                  className="bg-opacity-20 border-opacity-20 backdrop-blur-sm"
                >
                  {(detection.confidence * 100).toFixed(0)}%
                </Badge>
                {detection.metadata?.priority === 'high' && (
                  <Badge variant="error" size="sm" className="bg-red-500/20 border-red-500/30">
                    High Priority
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-4 text-xs font-medium text-slate-500">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-600 group-hover:bg-emerald-500 transition-colors" />
                  <span className="truncate max-w-[150px]">{detection.deviceName}</span>
                </div>
                {detection.location && (
                  <div className="hidden md:flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5" />
                    <span className="truncate max-w-[100px]">{detection.location.name}</span>
                  </div>
                )}
                <div className="hidden sm:flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{format(new Date(detection.timestamp), 'MMM d, yyyy')}</span>
                </div>
              </div>
            </div>

            <div className="text-right flex-shrink-0 z-10 pl-4 border-l border-slate-200 dark:border-slate-800/50">
              <div className="text-sm font-bold text-foreground font-mono group-hover:text-emerald-600 dark:group-hover:text-emerald-300 transition-colors">
                {format(new Date(detection.timestamp), 'HH:mm:ss')}
              </div>
              <div className="mt-1 flex justify-end">
                <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-emerald-500 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>
          </div>
        ))}

        {filteredDetections.length === 0 && detections.length > 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <Filter className="w-10 h-10 mb-3 opacity-30" />
            <p className="font-medium">No detections match your filters</p>
            <Button
              variant="ghost"
              onClick={() => {
                setSearchTerm('')
                setSelectedClass(null)
              }}
              className="mt-2 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10"
            >
              Clear filters
            </Button>
          </div>
        )}
      </div>

      {/* Detection Detail Modal */}
      {selectedDetection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md" onClick={() => setSelectedDetection(null)}>
          <div
            className="relative w-full max-w-2xl glass-panel spotlight-card rounded-2xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Local Noise Texture */}
            <div className="absolute inset-0 z-0 pointer-events-none opacity-[0.03]" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`
            }} />
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border dark:border-slate-700/50">
              <div className="flex items-center gap-3">
                <span className="text-3xl">
                  {animalEmojis[selectedDetection.className.toLowerCase()] || animalEmojis.default}
                </span>
                <div>
                  <h3 className="text-xl font-bold text-foreground capitalize">{selectedDetection.className}</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{selectedDetection.deviceName}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedDetection(null)}
                className="p-2 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            {/* Image */}
            {selectedDetection.imageUrl ? (
              <div className="relative aspect-video bg-slate-950">
                <img
                  src={selectedDetection.imageUrl}
                  alt={`${selectedDetection.className} detection`}
                  className="w-full h-full object-contain"
                />
                {/* Bounding box overlay indicator */}
                {selectedDetection.bbox && selectedDetection.bbox.length === 4 && (
                  <div className="absolute top-2 left-2 px-2 py-1 bg-red-500/80 rounded text-xs text-white font-medium">
                    Detection Area Marked
                  </div>
                )}
              </div>
            ) : (
              <div className="aspect-video bg-slate-950 flex items-center justify-center">
                <div className="text-center text-slate-600">
                  <ImageIcon className="w-16 h-16 mx-auto mb-2 opacity-30" />
                  <p>No image captured</p>
                </div>
              </div>
            )}

            {/* Details */}
            <div className="p-4 space-y-4">
              {/* Stats Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-100 dark:bg-slate-800/50 rounded-lg">
                  <div className="text-xs text-slate-500 mb-1">Confidence</div>
                  <div className="text-lg font-bold text-emerald-500 dark:text-emerald-400">
                    {(selectedDetection.confidence * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="p-3 bg-slate-100 dark:bg-slate-800/50 rounded-lg">
                  <div className="text-xs text-slate-500 mb-1">Time</div>
                  <div className="text-lg font-bold text-foreground">
                    {format(new Date(selectedDetection.timestamp), 'HH:mm:ss')}
                  </div>
                </div>
                <div className="p-3 bg-slate-100 dark:bg-slate-800/50 rounded-lg">
                  <div className="text-xs text-slate-500 mb-1">Date</div>
                  <div className="text-lg font-bold text-foreground">
                    {format(new Date(selectedDetection.timestamp), 'MMM d')}
                  </div>
                </div>
                <div className="p-3 bg-slate-100 dark:bg-slate-800/50 rounded-lg">
                  <div className="text-xs text-slate-500 mb-1">Priority</div>
                  <div className="text-lg font-bold text-foreground capitalize">
                    {selectedDetection.metadata?.priority || 'Normal'}
                  </div>
                </div>
              </div>

              {/* Location & Camera */}
              <div className="flex flex-wrap gap-3 text-sm">
                {selectedDetection.cameraId && (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-slate-800/50 rounded-lg text-slate-600 dark:text-slate-300">
                    <Camera className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                    <span>{selectedDetection.cameraId}</span>
                  </div>
                )}
                {selectedDetection.location && (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-slate-800/50 rounded-lg text-slate-600 dark:text-slate-300">
                    <MapPin className="w-4 h-4 text-red-500 dark:text-red-400" />
                    <span>{selectedDetection.location.name}</span>
                  </div>
                )}
                {selectedDetection.metadata?.processingTimeMs && (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-slate-800/50 rounded-lg text-slate-600 dark:text-slate-300">
                    <Zap className="w-4 h-4 text-yellow-500 dark:text-yellow-400" />
                    <span>{selectedDetection.metadata.processingTimeMs.toFixed(0)}ms</span>
                  </div>
                )}
              </div>

              {/* Event ID */}
              {selectedDetection.eventId && (
                <div className="text-xs text-slate-600 font-mono">
                  Event ID: {selectedDetection.eventId}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
