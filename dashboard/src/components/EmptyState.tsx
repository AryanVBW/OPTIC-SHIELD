import { ReactNode } from 'react'
import { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className = ''
}: EmptyStateProps) {
  return (
    <div className={`text-center py-12 ${className}`}>
      <div className="mb-4 flex justify-center">
        <div className="p-4 bg-surface-highlight rounded-full border border-border">
          <Icon className="w-12 h-12 text-slate-400 dark:text-slate-500" />
        </div>
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4 max-w-md mx-auto">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
