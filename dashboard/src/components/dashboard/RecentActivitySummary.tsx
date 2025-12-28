'use client'

import { Activity, Clock, ArrowRight, Eye } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Detection } from '@/types'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'

interface RecentActivitySummaryProps {
    detections: Detection[]
}

export function RecentActivitySummary({ detections }: RecentActivitySummaryProps) {
    const recentDetections = detections.slice(0, 7) // Show slightly more items since it's compact

    return (
        <Card variant="glass" className="h-full border-border dark:border-white/5">
            <CardHeader className="border-b border-border dark:border-slate-800/50 py-3 min-h-[60px] flex flex-row items-center justify-between">
                <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-nexus-accent" />
                    <span className="font-semibold text-white tracking-tight">Live Feed</span>
                </div>
                <Link href="/live-feed">
                    <Button variant="ghost" size="sm" className="h-8 text-xs text-slate-500 dark:text-slate-400 hover:text-foreground hover:bg-slate-100 dark:hover:bg-white/5 px-2">
                        View All <ArrowRight className="w-3 h-3 ml-1" />
                    </Button>
                </Link>
            </CardHeader>

            <CardContent className="p-0">
                <div className="divide-y divide-border dark:divide-slate-800/50">
                    {recentDetections.length === 0 ? (
                        <div className="p-8 text-center text-slate-500 text-sm">
                            No recent activity recorded
                        </div>
                    ) : (
                        recentDetections.map((detection) => (
                            <div key={detection.id} className="group flex items-center justify-between p-3 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-default">
                                <div className="flex items-center gap-3 overflow-hidden">
                                    <div className="w-1.5 h-1.5 rounded-full bg-nexus-accent animate-pulse" />
                                    <div className="flex flex-col min-w-0">
                                        <span className="text-sm font-medium text-foreground truncate group-hover:text-nexus-accent transition-colors">
                                            {detection.className}
                                        </span>
                                        <span className="text-xs text-slate-500 truncate flex items-center gap-1">
                                            {detection.deviceName}
                                        </span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 pl-2">
                                    <div className="text-xs text-slate-600 font-mono whitespace-nowrap">
                                        {formatDistanceToNow(new Date(detection.timestamp), { addSuffix: true })}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </CardContent>
        </Card>
    )
}
