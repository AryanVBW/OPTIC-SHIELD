'use client'

import { useState, useEffect } from 'react'
import { Clock, CheckCircle, XCircle, MessageSquare, Mail, Smartphone } from 'lucide-react'
import { AlertMessage } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { apiClient } from '@/lib/api-client'

export function AlertHistory() {
    const [history, setHistory] = useState<AlertMessage[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchHistory()
    }, [])

    const fetchHistory = async () => {
        try {
            const data = await apiClient.get<{ history: AlertMessage[] }>('/api/alerts/history?limit=50')
            setHistory(data.history || [])
        } catch (err) {
            console.error('Error fetching alert history:', err)
        } finally {
            setLoading(false)
        }
    }

    const getChannelIcon = (channel: string) => {
        switch (channel) {
            case 'whatsapp':
                return <MessageSquare className="w-4 h-4 text-green-500" />
            case 'sms':
                return <Smartphone className="w-4 h-4 text-blue-500" />
            case 'email':
                return <Mail className="w-4 h-4 text-purple-500" />
            default:
                return null
        }
    }

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'sent':
            case 'delivered':
                return <CheckCircle className="w-4 h-4 text-green-500" />
            case 'failed':
                return <XCircle className="w-4 h-4 text-red-500" />
            default:
                return <Clock className="w-4 h-4 text-yellow-500" />
        }
    }

    if (loading) {
        return (
            <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto"></div>
                <p className="text-slate-500 mt-2 text-sm">Loading history...</p>
            </div>
        )
    }

    if (history.length === 0) {
        return (
            <div className="p-8 text-center">
                <p className="text-slate-500">No alerts sent yet</p>
            </div>
        )
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full">
                <thead className="bg-slate-800/50 border-b border-border">
                    <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Time
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Recipient
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Channel
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Status
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Detection ID
                        </th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-border">
                    {history.map(message => (
                        <tr key={message.id} className="hover:bg-slate-800/30 transition-colors">
                            <td className="px-4 py-3 text-sm text-slate-300">
                                {message.sentAt
                                    ? new Date(message.sentAt).toLocaleString()
                                    : '-'}
                            </td>
                            <td className="px-4 py-3 text-sm font-medium text-foreground">
                                {message.recipientName}
                            </td>
                            <td className="px-4 py-3">
                                <div className="flex items-center gap-2">
                                    {getChannelIcon(message.channel)}
                                    <span className="text-sm capitalize">{message.channel}</span>
                                </div>
                            </td>
                            <td className="px-4 py-3">
                                <div className="flex items-center gap-2">
                                    {getStatusIcon(message.status)}
                                    <Badge
                                        variant={
                                            message.status === 'sent' || message.status === 'delivered'
                                                ? 'success'
                                                : message.status === 'failed'
                                                    ? 'error'
                                                    : 'warning'
                                        }
                                        size="sm"
                                    >
                                        {message.status}
                                    </Badge>
                                </div>
                            </td>
                            <td className="px-4 py-3 text-sm text-slate-400">
                                #{message.detectionId}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
