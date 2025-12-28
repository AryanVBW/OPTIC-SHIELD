interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  label?: string
}

const sizeStyles = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
  xl: 'w-16 h-16',
}

export function LoadingSpinner({ size = 'md', className = '', label }: LoadingSpinnerProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <div className="relative">
        <div className={`${sizeStyles[size]} border-4 border-slate-200 dark:border-slate-700 border-t-blue-500 rounded-full animate-spin`} />
      </div>
      {label && (
        <p className="text-sm text-slate-500 dark:text-slate-400 animate-pulse">{label}</p>
      )}
    </div>
  )
}
