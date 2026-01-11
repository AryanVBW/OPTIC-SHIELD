import { Shield, BarChart3, Camera, Activity, Settings, RefreshCw, Bell } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ConnectionStatus } from '@/components/ConnectionStatus'
import Link from 'next/link'

interface SidebarProps {
    onRefresh: () => void
    isRefreshing: boolean
}

export function Sidebar({ onRefresh, isRefreshing }: SidebarProps) {
    return (
        <aside className="w-72 hidden md:flex flex-col h-screen sticky top-0 border-r border-border bg-surface/30 backdrop-blur-2xl">
            {/* Logo Section */}
            <div className="p-8 pb-8 flex flex-col justify-center border-b border-white/5">
                <div className="flex items-center gap-4 mb-1">
                    <div className="relative group">
                        <div className="absolute inset-0 bg-primary-500/20 blur-xl rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-500" />
                        <Shield className="w-10 h-10 text-primary-500 relative z-10" />
                        <div className="absolute top-0 right-0 w-3 h-3 bg-primary-400 rounded-full animate-pulse z-20 shadow-[0_0_10px_rgba(74,222,128,0.5)]" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-foreground">
                            OPTIC<span className="text-primary-500">-SHIELD</span>
                        </h1>
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-medium tracking-wider uppercase">Wildlife Defense</p>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-6 space-y-2">
                <div className="mb-2 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Menu</div>
                <Link href="/" className="block w-full">
                    <Button
                        variant="ghost"
                        size="md"
                        className="w-full justify-start text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-slate-800/50 group"
                        icon={<BarChart3 className="w-5 h-5 text-slate-500 dark:text-slate-400 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors" />}
                    >
                        Dashboard
                    </Button>
                </Link>
                <Link href="/devices" className="block w-full">
                    <Button
                        variant="ghost"
                        size="md"
                        className="w-full justify-start text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-slate-800/50 group"
                        icon={<Camera className="w-5 h-5 text-slate-500 dark:text-slate-400 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors" />}
                    >
                        Devices
                    </Button>
                </Link>
                <Link href="/live-feed" className="block w-full">
                    <Button
                        variant="ghost"
                        size="md"
                        className="w-full justify-start text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-slate-800/50 group"
                        icon={<Activity className="w-5 h-5 text-slate-500 dark:text-slate-400 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors" />}
                    >
                        Detections
                    </Button>
                </Link>
                <Link href="/alerts" className="block w-full">
                    <Button
                        variant="ghost"
                        size="md"
                        className="w-full justify-start text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-slate-800/50 group"
                        icon={<Bell className="w-5 h-5 text-slate-500 dark:text-slate-400 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors" />}
                    >
                        Alerts
                    </Button>
                </Link>
                <Link href="/settings" className="block w-full">
                    <Button
                        variant="ghost"
                        size="md"
                        className="w-full justify-start text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-slate-800/50 group"
                        icon={<Settings className="w-5 h-5 text-slate-500 dark:text-slate-400 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors" />}
                    >
                        Settings
                    </Button>
                </Link>
            </nav>

            {/* Footer / Status */}
            <div className="p-6 border-t border-slate-800/60 bg-gradient-to-t from-slate-900/50 to-transparent">
                <div className="space-y-4">
                    <div className="glass-panel p-4 rounded-xl">
                        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">System Status</h3>
                        <ConnectionStatus />
                    </div>

                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onRefresh}
                        loading={isRefreshing}
                        icon={<RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />}
                        className="w-full border-slate-700/50 hover:bg-slate-800/50 hover:text-primary-400 transition-all font-medium"
                    >
                        Refresh Data
                    </Button>
                </div>
            </div>
        </aside>
    )
}
