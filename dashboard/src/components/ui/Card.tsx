import { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  hover?: boolean
  gradient?: boolean
  variant?: 'default' | 'glass' | 'neon'
  onClick?: () => void
}

export function Card({
  children,
  className = '',
  hover = false,
  gradient = false,
  variant = 'default',
  onClick
}: CardProps) {

  const variants = {
    default: 'bg-surface/30 dark:bg-slate-900/30 border border-border dark:border-white/5 backdrop-blur-xl',
    glass: 'glass-panel spotlight-card',
    neon: 'bg-slate-900/60 border border-primary-500/20 shadow-[0_0_15px_rgba(16,185,129,0.1)] backdrop-blur-xl'
  }

  return (
    <div
      className={`
        relative rounded-xl overflow-hidden
        ${variants[variant]}
        ${gradient ? 'bg-gradient-to-br from-white/10 to-transparent before:absolute before:inset-0 before:bg-gradient-to-br before:from-white/5 before:to-transparent before:pointer-events-none' : ''}
        ${hover ? 'transition-all duration-300 hover:border-slate-600/60 hover:shadow-lg hover:shadow-primary-900/10 hover:-translate-y-1' : ''}
        ${onClick ? 'cursor-pointer' : ''}
        ${className}
      `}
      onClick={onClick}
    >
      {/* Decorative top sheen */}
      {gradient && <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-slate-500/20 to-transparent"></div>}

      {children}
    </div>
  )
}

interface CardHeaderProps {
  children: ReactNode
  className?: string
}

export function CardHeader({ children, className = '' }: CardHeaderProps) {
  return (
    <div className={`px-6 py-5 border-b border-border dark:border-slate-700/30 ${className}`}>
      {children}
    </div>
  )
}

interface CardContentProps {
  children: ReactNode
  className?: string
}

export function CardContent({ children, className = '' }: CardContentProps) {
  return (
    <div className={`px-6 py-5 ${className}`}>
      {children}
    </div>
  )
}

interface CardTitleProps {
  children: ReactNode
  icon?: ReactNode
  badge?: ReactNode
  className?: string
}

export function CardTitle({ children, icon, badge, className = '' }: CardTitleProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {icon && (
        <div className="p-2 rounded-lg bg-white/50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 border border-border dark:border-slate-700/50 shadow-sm">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-foreground flex-1 tracking-tight">{children}</h3>
      {badge && <div className="ml-2">{badge}</div>}
    </div>
  )
}
