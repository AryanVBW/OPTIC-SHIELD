'use client'

import { useState, useEffect } from 'react'
import { Device } from '@/types'
import { apiClient } from '@/lib/api-client'
import { EnhancedDeviceCard } from '@/components/EnhancedDeviceCard'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Alert } from '@/components/ui/Alert'
import { Sidebar } from '@/components/layout/Sidebar'
import { Camera, Server, Plus, Wifi } from 'lucide-react'
import { Button } from '@/components/ui/Button'

export default function DevicesPage() {
    const [devices, setDevices] = useState<Device[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [refreshing, setRefreshing] = useState(false)
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

    useEffect(() => {
        fetchDevices()
    }, [])

    const fetchDevices = async (showRefreshing = false) => {
        if (showRefreshing) setRefreshing(true)

        try {
            const { devices } = await apiClient.get<{ devices: Device[] }>('/api/devices')
            setDevices(devices || [])
            setError(null)
            setLastUpdate(new Date())
        } catch (err) {
            console.error('Devices fetch error:', err)
            setError(err instanceof Error ? err.message : 'Failed to fetch devices')
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }

    const handleRefresh = () => {
        fetchDevices(true)
    }

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <LoadingSpinner label="Loading Devices..." size="lg" />
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-background text-foreground flex font-sans">
            <Sidebar onRefresh={handleRefresh} isRefreshing={refreshing} />

            <main className="flex-1 overflow-auto relative p-6">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-foreground tracking-tight mb-1 flex items-center gap-3">
                            <Camera className="w-8 h-8 text-nexus-accent" />
                            Connected Devices
                        </h1>
                        <p className="text-slate-500 dark:text-slate-400">Manage and monitor your camera grid</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <Button variant="primary" icon={<Plus className="w-4 h-4" />}>
                            Add Device
                        </Button>
                    </div>
                </div>

                {error && (
                    <Alert variant="error" title="Device Error" onClose={() => setError(null)} className="mb-6">
                        {error}
                    </Alert>
                )}

                {devices.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 bg-surface/20 dark:bg-slate-900/20 border border-dashed border-border dark:border-slate-800 rounded-2xl">
                        <div className="relative group mb-6">
                            <div className="absolute inset-0 bg-primary-500/20 blur-2xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                            <Server className="w-20 h-20 text-slate-400 dark:text-slate-700 relative z-10" />
                        </div>
                        <h3 className="text-xl font-bold text-foreground dark:text-slate-300 mb-2">No Devices Found</h3>
                        <p className="text-slate-500 max-w-md text-center mb-6">
                            Connect your edge devices to start monitoring wildlife activity.
                        </p>
                        <Button variant="outline">Learn How to Connect</Button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                        {devices.map(device => (
                            <div key={device.id} className="h-full">
                                <EnhancedDeviceCard device={device} />
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    )
}
