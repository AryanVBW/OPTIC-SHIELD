'use client'

import { DashboardStats } from '@/types'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface ActivityChartProps {
  stats: DashboardStats | null
}

export function ActivityChart({ stats }: ActivityChartProps) {
  if (!stats?.hourlyDetections || stats.hourlyDetections.length === 0) {
    return (
      <div className="h-[300px] flex items-center justify-center text-slate-500 flex-col gap-3 border border-dashed border-border rounded-xl bg-surface/30">
        <div className="w-12 h-12 rounded-full bg-surface-highlight flex items-center justify-center">
          <svg className="w-6 h-6 text-slate-400 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <p className="font-medium text-sm">No detection activity recorded yet</p>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={stats.hourlyDetections} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.3} />
          </linearGradient>
          <linearGradient id="colorCountHover" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.9} />
            <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.4} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.3} />
        <XAxis
          dataKey="hour"
          stroke="#64748b"
          tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
          tickLine={false}
          axisLine={false}
          dy={10}
        />
        <YAxis
          stroke="#64748b"
          tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value) => `${value}`}
        />
        <Tooltip
          cursor={{ fill: '#334155', opacity: 0.2 }}
          content={({ active, payload, label }) => {
            if (active && payload && payload.length) {
              return (
                <div className="bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl border border-border p-3 rounded-lg shadow-xl">
                  <p className="text-slate-500 dark:text-slate-400 text-xs font-semibold mb-1 uppercase tracking-wider">{label}</p>
                  <p className="text-foreground text-sm font-bold flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    {payload[0].value} Detections
                  </p>
                </div>
              )
            }
            return null
          }}
        />
        <Bar
          dataKey="count"
          fill="url(#colorCount)"
          radius={[6, 6, 0, 0]}
          barSize={32}
          animationDuration={1500}
          animationEasing="ease-out"
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
