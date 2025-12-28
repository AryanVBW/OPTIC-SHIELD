import { ReactNode } from 'react'

type Status = 'online' | 'offline' | 'warning' | 'error' | 'connecting'

interface StatusIndicatorProps {
  status: Status
  label?: string
  showPulse?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const statusConfig: Record<Status, { color: string; bgColor: string; label: string }> = {
  online: {
    color: 'bg-emerald-500',
    bgColor: 'bg-emerald-500/20',
    label: 'Online',
  },
  offline: {
    color: 'bg-slate-500',
    bgColor: 'bg-slate-500/20',
    label: 'Offline',
  },
  warning: {
    color: 'bg-amber-500',
    bgColor: 'bg-amber-500/20',
    label: 'Warning',
  },
  error: {
    color: 'bg-red-500',
    bgColor: 'bg-red-500/20',
    label: 'Error',
  },
  connecting: {
    color: 'bg-blue-500',
    bgColor: 'bg-blue-500/20',
    label: 'Connecting',
  },
}

const sizeStyles = {
  sm: 'w-2 h-2',
  md: 'w-2.5 h-2.5',
  lg: 'w-3 h-3',
}

export function StatusIndicator({
  status,
  label,
  showPulse = true,
  size = 'md',
  className = ''
}: StatusIndicatorProps) {
  const config = statusConfig[status]
  const displayLabel = label || config.label

  return (
    <div className={`inline-flex items-center gap-2.5 ${className}`}>
      <div className="relative flex items-center justify-center">
        <div className={`rounded-full ${sizeStyles[size]} ${config.color} shadow-lg shadow-${config.color.replace('bg-', '')}/50 relative z-10`} />

        {showPulse && status === 'online' && (
          <>
            <div className={`absolute inset-0 rounded-full ${config.color} animate-ping opacity-75 scale-150`} />
            <div className={`absolute inset-0 rounded-full ${config.color} opacity-20 scale-[2.5] blur-sm`} />
          </>
        )}

        {showPulse && status === 'connecting' && (
          <div className={`absolute inset-0 rounded-full ${config.color} animate-pulse scale-150 opacity-60`} />
        )}

        {showPulse && status === 'warning' && (
          <div className={`absolute inset-0 rounded-full ${config.color} animate-pulse scale-150 opacity-40`} />
        )}

        {showPulse && status === 'error' && (
          <div className={`absolute inset-0 rounded-full ${config.color} opacity-30 scale-[2.0] blur-sm`} />
        )}
      </div>
      {displayLabel && (
        <span className={`text-sm font-medium ${status === 'online' ? 'text-foreground dark:text-slate-200' : 'text-slate-500 dark:text-slate-400'}`}>
          {displayLabel}
        </span>
      )}
    </div>
  )
}
