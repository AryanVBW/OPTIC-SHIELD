'use client'

import { Camera, Activity, TrendingUp, Zap, ArrowUp, ArrowDown } from 'lucide-react'
import { DashboardStats } from '@/types'
import { Card, CardContent } from './ui/Card'

interface EnhancedStatsOverviewProps {
  stats: DashboardStats | null
}

export function EnhancedStatsOverview({ stats }: EnhancedStatsOverviewProps) {
  const statCards = [
    {
      label: 'Active Devices',
      value: stats?.onlineDevices || 0,
      total: stats?.totalDevices || 0,
      subValue: `${stats?.totalDevices || 0} total devices`,
      icon: Camera,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/20',
      trend: null,
      gradientFrom: 'from-emerald-500/20',
      gradientTo: 'to-teal-500/5',
    },
    {
      label: 'Today\'s Detections',
      value: stats?.totalDetections24h || 0,
      subValue: 'Last 24 hours',
      icon: Activity,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/20',
      trend: 12, // Mock trend for visualization
      gradientFrom: 'from-blue-500/20',
      gradientTo: 'to-indigo-500/5',
    },
    {
      label: 'Weekly Total',
      value: stats?.totalDetectionsWeek || 0,
      subValue: 'Last 7 days',
      icon: TrendingUp,
      color: 'text-violet-400',
      bgColor: 'bg-violet-500/10',
      borderColor: 'border-violet-500/20',
      trend: 5, // Mock trend
      gradientFrom: 'from-violet-500/20',
      gradientTo: 'to-fuchsia-500/5',
    },
    {
      label: 'Most Detected',
      value: stats?.classDistribution
        ? (Object.keys(stats.classDistribution)[0] || 'None')
        : 'None',
      subValue: stats?.classDistribution
        ? `${Object.values(stats.classDistribution)[0] || 0} sightings`
        : 'No data yet',
      icon: Zap,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      borderColor: 'border-amber-500/20',
      trend: null,
      gradientFrom: 'from-amber-500/20',
      gradientTo: 'to-orange-500/5',
    }
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {statCards.map((stat, index) => (
        <Card
          key={index}
          hover
          className={`border-border dark:border-slate-800 bg-surface/50 dark:bg-slate-900/40 overflow-hidden relative group`}
        >
          {/* Background Gradient */}
          <div className={`absolute inset-0 bg-gradient-to-br ${stat.gradientFrom} ${stat.gradientTo} opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />

          <CardContent className="p-6 relative">
            <div className="flex items-start justify-between mb-4">
              <div className={`p-3 rounded-xl ${stat.bgColor} border border-white/5 backdrop-blur-md shadow-inner`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
              {stat.trend !== null && (
                <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full bg-surface-highlight dark:bg-slate-800/50 border border-border dark:border-slate-700/50 ${stat.trend > 0 ? 'text-emerald-500 dark:text-emerald-400' : 'text-rose-500 dark:text-rose-400'
                  }`}>
                  {stat.trend > 0 ? (
                    <ArrowUp className="w-3 h-3" />
                  ) : (
                    <ArrowDown className="w-3 h-3" />
                  )}
                  {Math.abs(stat.trend)}%
                </div>
              )}
            </div>

            <div className="space-y-1">
              <div className="text-sm font-medium text-slate-500 dark:text-slate-400 group-hover:text-foreground dark:group-hover:text-slate-300 transition-colors">
                {stat.label}
              </div>
              <div className="text-3xl font-bold text-foreground capitalize tracking-tight">
                {stat.value}
                {stat.total !== undefined && (
                  <span className="text-lg text-slate-600 font-medium ml-1.5">/ {stat.total}</span>
                )}
              </div>
              <div className="text-xs text-slate-500 mt-2 font-medium">
                {stat.subValue}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
