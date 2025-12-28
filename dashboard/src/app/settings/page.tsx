'use client'

import { useState } from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Settings, Moon, Sun, Monitor, Zap, Power } from 'lucide-react'
import { useSettings } from '@/context/SettingsContext'

export default function SettingsPage() {
    const [refreshing, setRefreshing] = useState(false)
    const { theme, setTheme, enableAnimations, setEnableAnimations, enableTexture, setEnableTexture } = useSettings()

    const handleRefresh = () => {
        setRefreshing(true)
        setTimeout(() => setRefreshing(false), 1000)
    }

    return (
        <div className="min-h-screen bg-background/80 text-foreground flex font-sans transition-colors duration-300">
            <Sidebar onRefresh={handleRefresh} isRefreshing={refreshing} />

            <main className="flex-1 overflow-auto relative p-6">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-foreground tracking-tight mb-1 flex items-center gap-3">
                            <Settings className="w-8 h-8 text-nexus-accent" />
                            Configuration
                        </h1>
                        <p className="text-slate-500 dark:text-slate-400">Customize appearance and system behavior</p>
                    </div>
                </div>

                <div className="max-w-4xl space-y-6">

                    {/* Appearance Settings */}
                    <Card variant="glass">
                        <CardHeader>
                            <CardTitle icon={<Monitor className="w-5 h-5 text-primary-400" />}>
                                Appearance
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">

                            {/* Theme Selection */}
                            <div className="space-y-3">
                                <h3 className="text-sm font-medium text-foreground">Interface Theme</h3>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                    <button
                                        onClick={() => setTheme('dark')}
                                        className={`flex items-center justify-center gap-2 p-3 rounded-lg border transition-all ${theme === 'dark' ? 'bg-primary-500/20 border-primary-500 text-primary-600 dark:text-primary-400' : 'bg-surface border-border text-slate-500 hover:bg-surface-highlight'}`}
                                    >
                                        <Moon className="w-4 h-4" />
                                        <span className="text-sm font-medium">Dark</span>
                                    </button>
                                    <button
                                        onClick={() => setTheme('light')}
                                        className={`flex items-center justify-center gap-2 p-3 rounded-lg border transition-all ${theme === 'light' ? 'bg-primary-500/20 border-primary-500 text-primary-600 dark:text-primary-400' : 'bg-surface border-border text-slate-500 hover:bg-surface-highlight'}`}
                                    >
                                        <Sun className="w-4 h-4" />
                                        <span className="text-sm font-medium">Light</span>
                                    </button>
                                    <button
                                        onClick={() => setTheme('system')}
                                        className={`flex items-center justify-center gap-2 p-3 rounded-lg border transition-all ${theme === 'system' ? 'bg-primary-500/20 border-primary-500 text-primary-600 dark:text-primary-400' : 'bg-surface border-border text-slate-500 hover:bg-surface-highlight'}`}
                                    >
                                        <Monitor className="w-4 h-4" />
                                        <span className="text-sm font-medium">System</span>
                                    </button>
                                </div>
                            </div>

                            {/* Animation Control */}
                            <div className="flex items-center justify-between p-4 rounded-lg bg-surface/50 border border-border">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <Zap className={`w-4 h-4 ${enableAnimations ? 'text-amber-400' : 'text-slate-500'}`} />
                                        <h3 className="text-sm font-medium text-white">Dynamic Backgrounds</h3>
                                    </div>
                                    <p className="text-xs text-slate-400 max-w-md">
                                        Enable or disable high-performance 3D background animations and particle effects.
                                        Disabling this may improve performance on older devices.
                                    </p>
                                </div>
                                <button
                                    onClick={() => setEnableAnimations(!enableAnimations)}
                                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${enableAnimations ? 'bg-primary-600' : 'bg-slate-700'}`}
                                >
                                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${enableAnimations ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>

                            {/* Texture Control */}
                            <div className="flex items-center justify-between p-4 rounded-lg bg-surface/50 border border-border">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <div className={`w-4 h-4 rounded-full border ${enableTexture ? 'border-purple-400 bg-purple-400/20' : 'border-slate-500 bg-transparent'}`} />
                                        <h3 className="text-sm font-medium text-white">Grain Texture</h3>
                                    </div>
                                    <p className="text-xs text-slate-400 max-w-md">
                                        Enable or disable the cinematic film grain overlay.
                                    </p>
                                </div>
                                <button
                                    onClick={() => setEnableTexture(!enableTexture)}
                                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${enableTexture ? 'bg-primary-600' : 'bg-slate-700'}`}
                                >
                                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${enableTexture ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>

                        </CardContent>
                    </Card>

                    {/* System Info (Static for now, but good for context) */}
                    <Card variant="glass">
                        <CardHeader>
                            <CardTitle icon={<Power className="w-5 h-5 text-emerald-400" />}>
                                System Information
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="p-3 rounded-lg bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800">
                                    <span className="block text-xs text-slate-500 mb-1">Version</span>
                                    <span className="text-sm font-mono text-foreground">v1.2.4</span>
                                </div>
                                <div className="p-3 rounded-lg bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800">
                                    <span className="block text-xs text-slate-500 mb-1">Environment</span>
                                    <span className="text-sm font-mono text-emerald-600 dark:text-emerald-400">Production</span>
                                </div>
                                <div className="p-3 rounded-lg bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800">
                                    <span className="block text-xs text-slate-500 mb-1">Build ID</span>
                                    <span className="text-sm font-mono text-slate-600 dark:text-slate-300">#8F2A9C</span>
                                </div>
                                <div className="p-3 rounded-lg bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800">
                                    <span className="block text-xs text-slate-500 mb-1">Region</span>
                                    <span className="text-sm font-mono text-slate-600 dark:text-slate-300">US-East</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                </div>
            </main>
        </div>
    )
}
