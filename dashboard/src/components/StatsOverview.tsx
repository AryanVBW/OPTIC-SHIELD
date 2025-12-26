'use client'

import { Camera, Activity, TrendingUp, Clock } from 'lucide-react'
import { DashboardStats } from '@/types'

interface StatsOverviewProps {
  stats: DashboardStats | null
}

export default function StatsOverview({ stats }: StatsOverviewProps) {
  const statCards = [
    {
      label: 'Total Devices',
      value: stats?.totalDevices || 0,
      subValue: `${stats?.onlineDevices || 0} online`,
      icon: Camera,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10'
    },
    {
      label: 'Detections (24h)',
      value: stats?.totalDetections24h || 0,
      subValue: 'Last 24 hours',
      icon: Activity,
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10'
    },
    {
      label: 'Weekly Total',
      value: stats?.totalDetectionsWeek || 0,
      subValue: 'Last 7 days',
      icon: TrendingUp,
      color: 'text-green-400',
      bgColor: 'bg-green-500/10'
    },
    {
      label: 'Top Species',
      value: stats?.classDistribution 
        ? Object.keys(stats.classDistribution)[0] || '-'
        : '-',
      subValue: stats?.classDistribution
        ? `${Object.values(stats.classDistribution)[0] || 0} detections`
        : 'No data',
      icon: Clock,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10'
    }
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards.map((stat, index) => (
        <div
          key={index}
          className="bg-slate-800 rounded-xl border border-slate-700 p-5"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm text-slate-400">{stat.label}</span>
            <div className={`p-2 rounded-lg ${stat.bgColor}`}>
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
            </div>
          </div>
          <div className="text-2xl font-bold text-white capitalize">
            {stat.value}
          </div>
          <div className="text-sm text-slate-500 mt-1">
            {stat.subValue}
          </div>
        </div>
      ))}
    </div>
  )
}
