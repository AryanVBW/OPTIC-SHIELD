'use client'

import { AlertTriangle, CheckCircle2, Server, Wifi, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Device } from '@/types'

interface SystemHealthProps {
    devices: Device[]
    onRefresh: () => void
    isRefreshing: boolean
}

export function SystemHealth({ devices, onRefresh, isRefreshing }: SystemHealthProps) {
    const offlineDevices = devices.filter(d => d.status === 'offline')
    const errorDevices = devices.filter(d => d.status === 'error')
    const totalIssues = offlineDevices.length + errorDevices.length

    const healthScore = Math.max(0, 100 - (totalIssues * 15)) // Simple scoring logic

    let statusColor = 'text-emerald-400'
    let statusText = 'Operational'
    let StatusIcon = CheckCircle2

    if (totalIssues > 0 && totalIssues <= 2) {
        statusColor = 'text-amber-400'
        statusText = 'Degraded'
        StatusIcon = AlertTriangle
    } else if (totalIssues > 2) {
        statusColor = 'text-rose-400'
        statusText = 'Critical'
        StatusIcon = AlertTriangle
    }

    return (
        <Card className="border-border bg-surface/40 backdrop-blur-md overflow-hidden relative group">
            <div className={`absolute inset-0 bg-gradient-to-r ${totalIssues === 0 ? 'from-emerald-500/10 to-teal-500/5' : 'from-amber-500/10 to-rose-500/5'} opacity-50`} />

            <CardContent className="p-0 relative">
                <div className="flex flex-col md:flex-row items-stretch">
                    {/* Status Section */}
                    <div className="flex-1 p-6 border-b md:border-b-0 md:border-r border-slate-800/50 flex items-center justify-between gap-6">
                        <div className="flex items-center gap-4">
                            <div className={`p-3 rounded-full ${totalIssues === 0 ? 'bg-emerald-500/20' : 'bg-amber-500/20'} ring-1 ring-white/10`}>
                                <StatusIcon className={`w-8 h-8 ${statusColor}`} />
                            </div>
                            <div>
                                <div className="text-sm text-slate-500 dark:text-slate-400 font-medium uppercase tracking-wider mb-1">System Status</div>
                                <div className={`text-2xl font-bold ${statusColor} tracking-tight`}>{statusText}</div>
                            </div>
                        </div>

                        {/* Health Score */}
                        <div className="text-right hidden sm:block">
                            <div className="text-sm text-slate-500 font-medium mb-1">Health Score</div>
                            <div className="text-3xl font-mono font-bold text-foreground">{healthScore}%</div>
                        </div>
                    </div>

                    {/* Metrics Section */}
                    <div className="flex-1 p-6 flex items-center justify-around gap-4 bg-white/5">
                        <div className="text-center group/metric cursor-default">
                            <div className="flex items-center justify-center gap-2 text-slate-500 dark:text-slate-400 mb-1 group-hover/metric:text-foreground transition-colors">
                                <Server className="w-4 h-4" />
                                <span className="text-xs font-semibold uppercase">Devices</span>
                            </div>
                            <div className="text-xl font-bold text-foreground">{devices.length}</div>
                        </div>

                        <div className="w-px h-10 bg-slate-700/50" />

                        <div className="text-center group/metric cursor-default">
                            <div className="flex items-center justify-center gap-2 text-slate-500 dark:text-slate-400 mb-1 group-hover/metric:text-emerald-500 dark:group-hover/metric:text-emerald-400 transition-colors">
                                <Wifi className="w-4 h-4" />
                                <span className="text-xs font-semibold uppercase">Online</span>
                            </div>
                            <div className="text-xl font-bold text-emerald-400">
                                {devices.filter(d => d.status === 'online').length}
                            </div>
                        </div>

                        <div className="w-px h-10 bg-slate-700/50" />

                        <div className="text-center group/metric cursor-default">
                            <div className="flex items-center justify-center gap-2 text-slate-500 dark:text-slate-400 mb-1 group-hover/metric:text-rose-500 dark:group-hover/metric:text-rose-400 transition-colors">
                                <AlertTriangle className="w-4 h-4" />
                                <span className="text-xs font-semibold uppercase">Offline</span>
                            </div>
                            <div className={`text-xl font-bold ${offlineDevices.length > 0 ? 'text-rose-400' : 'text-slate-500'}`}>
                                {offlineDevices.length}
                            </div>
                        </div>
                    </div>

                    {/* Action Section */}
                    <div className="p-4 flex items-center justify-center">
                        <button
                            onClick={onRefresh}
                            className={`p-3 rounded-xl hover:bg-white/5 text-slate-400 hover:text-white transition-all ${isRefreshing ? 'animate-spin text-emerald-400' : ''}`}
                            title="Refresh System Status"
                        >
                            <RefreshCw className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Issues List (if any) */}
                {totalIssues > 0 && (
                    <div className="bg-rose-500/10 border-t border-rose-500/20 py-2 px-6 flex items-center gap-2 text-sm text-rose-200">
                        <AlertTriangle className="w-4 h-4 text-rose-400" />
                        <span>Attention Needed:</span>
                        <div className="flex gap-2">
                            {offlineDevices.map(d => (
                                <Badge key={d.id} variant="error" size="sm" className="px-1.5 py-0 text-[10px] h-5">
                                    {d.name} Offline
                                </Badge>
                            ))}
                            {errorDevices.map(d => (
                                <Badge key={d.id} variant="error" size="sm" className="px-1.5 py-0 text-[10px] h-5">
                                    {d.name} Error
                                </Badge>
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    )
}
