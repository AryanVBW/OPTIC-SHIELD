'use client'

import { useState, useEffect } from 'react'
import { Bell, Users, Send, History, AlertCircle, CheckCircle, XCircle, Wifi, WifiOff } from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { RecipientManager } from '@/components/alerts/RecipientManager'
import { BulkAlertSender } from '@/components/alerts/BulkAlertSender'
import { AlertHistory } from '@/components/alerts/AlertHistory'
import { AlertRecipient, AlertStats } from '@/types'
import { apiClient } from '@/lib/api-client'

export default function AlertsPage() {
    const [recipients, setRecipients] = useState<AlertRecipient[]>([])
    const [stats, setStats] = useState<AlertStats | null>(null)
    const [serviceStatus, setServiceStatus] = useState<{
        whatsapp: boolean
        sms: boolean
        email: boolean
    } | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [refreshing, setRefreshing] = useState(false)

    useEffect(() => {
        fetchData()
    }, [])

    const fetchData = async () => {
        try {
            const [recipientsData, historyData, statusData] = await Promise.all([
                apiClient.get<{ recipients: AlertRecipient[] }>('/api/alerts/recipients'),
                apiClient.get<{ stats: AlertStats }>('/api/alerts/history'),
                apiClient.get<{ status: any }>('/api/alerts/send/status'),
            ])

            setRecipients(recipientsData.recipients || [])
            setStats(historyData.stats)
            setServiceStatus(statusData.status)
            setError(null)
        } catch (err) {
            console.error('Error fetching alerts data:', err)
            setError(err instanceof Error ? err.message : 'Failed to load alerts data')
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }

    const handleRefresh = () => {
        setRefreshing(true)
        fetchData()
    }

    const handleRecipientChange = () => {
        fetchData()
    }

    const handleAlertSent = () => {
        fetchData()
    }

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <div className="text-center">
                    <Bell className="w-16 h-16 text-primary-500 mx-auto mb-4 animate-pulse" />
                    <p className="text-slate-400">Loading Alert System...</p>
                </div>
            </div>
        )
    }

    const activeChannels = serviceStatus
        ? Object.entries(serviceStatus).filter(([_, active]) => active).length
        : 0

    return (
        <div className="min-h-screen bg-background/80 text-foreground flex font-sans">
            <Sidebar onRefresh={handleRefresh} isRefreshing={refreshing} />

            <main className="flex-1 overflow-auto p-4 md:p-6 space-y-6">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold text-foreground tracking-tight mb-1">
                            Alert Management
                        </h1>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                            Send wildlife detection alerts via WhatsApp, SMS, and Email
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="glass-panel px-4 py-2 rounded-lg">
                            <div className="flex items-center gap-2">
                                {activeChannels === 3 ? (
                                    <Wifi className="w-4 h-4 text-green-500" />
                                ) : (
                                    <WifiOff className="w-4 h-4 text-yellow-500" />
                                )}
                                <span className="text-sm font-medium">
                                    {activeChannels}/3 Channels Active
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {error && (
                    <Alert variant="error" title="Error" onClose={() => setError(null)}>
                        {error}
                    </Alert>
                )}

                {/* Service Status Warning */}
                {serviceStatus && activeChannels < 3 && (
                    <Alert variant="warning" title="Some services are not configured">
                        <div className="space-y-2">
                            <p>Configure the following environment variables to enable all channels:</p>
                            <ul className="list-disc list-inside text-sm space-y-1">
                                {!serviceStatus.whatsapp && (
                                    <li>WhatsApp/SMS: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN</li>
                                )}
                                {!serviceStatus.email && <li>Email: SENDGRID_API_KEY</li>}
                            </ul>
                        </div>
                    </Alert>
                )}

                {/* Statistics Overview */}
                {stats && (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <Card variant="glass" className="border-border">
                            <CardContent className="p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                                            Total Sent
                                        </p>
                                        <p className="text-2xl font-bold text-foreground">{stats.totalSent}</p>
                                    </div>
                                    <CheckCircle className="w-8 h-8 text-green-500 opacity-50" />
                                </div>
                            </CardContent>
                        </Card>

                        <Card variant="glass" className="border-border">
                            <CardContent className="p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                                            Failed
                                        </p>
                                        <p className="text-2xl font-bold text-foreground">{stats.totalFailed}</p>
                                    </div>
                                    <XCircle className="w-8 h-8 text-red-500 opacity-50" />
                                </div>
                            </CardContent>
                        </Card>

                        <Card variant="glass" className="border-border">
                            <CardContent className="p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                                            Recipients
                                        </p>
                                        <p className="text-2xl font-bold text-foreground">{recipients.length}</p>
                                    </div>
                                    <Users className="w-8 h-8 text-blue-500 opacity-50" />
                                </div>
                            </CardContent>
                        </Card>

                        <Card variant="glass" className="border-border">
                            <CardContent className="p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                                            Success Rate
                                        </p>
                                        <p className="text-2xl font-bold text-foreground">
                                            {stats.totalSent + stats.totalFailed > 0
                                                ? Math.round((stats.totalSent / (stats.totalSent + stats.totalFailed)) * 100)
                                                : 0}
                                            %
                                        </p>
                                    </div>
                                    <AlertCircle className="w-8 h-8 text-primary-500 opacity-50" />
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Recipient Manager */}
                    <Card variant="glass" className="border-border">
                        <CardHeader className="border-b border-border">
                            <CardTitle icon={<Users className="w-5 h-5 text-primary-400" />}>
                                Recipients
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <RecipientManager
                                recipients={recipients}
                                onRecipientChange={handleRecipientChange}
                            />
                        </CardContent>
                    </Card>

                    {/* Bulk Alert Sender */}
                    <Card variant="glass" className="border-border">
                        <CardHeader className="border-b border-border">
                            <CardTitle icon={<Send className="w-5 h-5 text-primary-400" />}>
                                Send Alerts
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-6">
                            <BulkAlertSender
                                recipients={recipients}
                                serviceStatus={serviceStatus}
                                onAlertSent={handleAlertSent}
                            />
                        </CardContent>
                    </Card>
                </div>

                {/* Alert History */}
                <Card variant="glass" className="border-border">
                    <CardHeader className="border-b border-border">
                        <CardTitle icon={<History className="w-5 h-5 text-primary-400" />}>
                            Alert History
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                        <AlertHistory />
                    </CardContent>
                </Card>
            </main>
        </div>
    )
}
