'use client'

import { useState, useEffect } from 'react'
import { Send, MessageSquare, Mail, Smartphone, Loader2 } from 'lucide-react'
import { AlertRecipient, Detection } from '@/types'
import { Button } from '@/components/ui/Button'
import { apiClient } from '@/lib/api-client'

interface BulkAlertSenderProps {
    recipients: AlertRecipient[]
    serviceStatus: {
        whatsapp: boolean
        sms: boolean
        email: boolean
    } | null
    onAlertSent: () => void
}

export function BulkAlertSender({ recipients, serviceStatus, onAlertSent }: BulkAlertSenderProps) {
    const [recentDetections, setRecentDetections] = useState<Detection[]>([])
    const [selectedDetections, setSelectedDetections] = useState<number[]>([])
    const [selectedRecipients, setSelectedRecipients] = useState<string[]>([])
    const [selectedChannels, setSelectedChannels] = useState<('whatsapp' | 'sms' | 'email')[]>([])
    const [customMessage, setCustomMessage] = useState('')
    const [sending, setSending] = useState(false)
    const [progress, setProgress] = useState<string | null>(null)
    const [result, setResult] = useState<{ sent: number; failed: number } | null>(null)

    useEffect(() => {
        fetchRecentDetections()
    }, [])

    const fetchRecentDetections = async () => {
        try {
            const data = await apiClient.get<{ detections: Detection[] }>('/api/detections?limit=10')
            setRecentDetections(data.detections || [])
        } catch (err) {
            console.error('Error fetching detections:', err)
        }
    }

    const toggleDetection = (id: number) => {
        setSelectedDetections(prev =>
            prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id]
        )
    }

    const toggleRecipient = (id: string) => {
        setSelectedRecipients(prev =>
            prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
        )
    }

    const toggleChannel = (channel: 'whatsapp' | 'sms' | 'email') => {
        setSelectedChannels(prev =>
            prev.includes(channel) ? prev.filter(c => c !== channel) : [...prev, channel]
        )
    }

    const selectAllRecipients = () => {
        const activeRecipientIds = recipients.filter(r => r.active).map(r => r.id)
        setSelectedRecipients(activeRecipientIds)
    }

    const handleSend = async () => {
        if (selectedDetections.length === 0) {
            alert('Please select at least one detection')
            return
        }
        if (selectedRecipients.length === 0) {
            alert('Please select at least one recipient')
            return
        }
        if (selectedChannels.length === 0) {
            alert('Please select at least one channel')
            return
        }

        if (!confirm(`Send alerts to ${selectedRecipients.length} recipient(s) via ${selectedChannels.join(', ')}?`)) {
            return
        }

        setSending(true)
        setProgress('Sending alerts...')
        setResult(null)

        try {
            const response = await apiClient.post<{ summary: { sent: number; failed: number } }>(
                '/api/alerts/send',
                {
                    detectionIds: selectedDetections,
                    recipientIds: selectedRecipients,
                    channels: selectedChannels,
                    customMessage: customMessage.trim() || undefined,
                }
            )

            setResult(response.summary)
            setProgress(null)

            // Clear selections
            setSelectedDetections([])
            setSelectedRecipients([])
            setSelectedChannels([])
            setCustomMessage('')

            onAlertSent()
        } catch (err: any) {
            alert(err.message || 'Failed to send alerts')
            setProgress(null)
        } finally {
            setSending(false)
        }
    }

    const activeRecipients = recipients.filter(r => r.active)

    return (
        <div className="space-y-6">
            {/* Result Display */}
            {result && (
                <div className="bg-green-500/10 border border-green-500/50 text-green-400 p-4 rounded-lg">
                    <p className="font-semibold mb-1">Alerts Sent Successfully!</p>
                    <p className="text-sm">
                        Sent: {result.sent} | Failed: {result.failed}
                    </p>
                </div>
            )}

            {/* Recent Detections */}
            <div>
                <h3 className="text-sm font-semibold mb-3 text-slate-300">Select Detections</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                    {recentDetections.length === 0 ? (
                        <p className="text-sm text-slate-500 text-center py-4">No recent detections</p>
                    ) : (
                        recentDetections.map(detection => (
                            <label
                                key={detection.id}
                                className="flex items-center gap-3 p-3 glass-panel rounded-lg cursor-pointer hover:bg-slate-700/50 transition-colors"
                            >
                                <input
                                    type="checkbox"
                                    checked={selectedDetections.includes(detection.id)}
                                    onChange={() => toggleDetection(detection.id)}
                                    className="w-4 h-4"
                                />
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium text-sm">{detection.className}</p>
                                    <p className="text-xs text-slate-500">
                                        {new Date(detection.timestamp).toLocaleString()} • {(detection.confidence * 100).toFixed(0)}%
                                    </p>
                                </div>
                            </label>
                        ))
                    )}
                </div>
            </div>

            {/* Recipient Selection */}
            <div>
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-slate-300">Select Recipients</h3>
                    <button
                        onClick={selectAllRecipients}
                        className="text-xs text-primary-400 hover:text-primary-300"
                    >
                        Select All
                    </button>
                </div>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                    {activeRecipients.length === 0 ? (
                        <p className="text-sm text-slate-500 text-center py-4">No active recipients</p>
                    ) : (
                        activeRecipients.map(recipient => (
                            <label
                                key={recipient.id}
                                className="flex items-center gap-3 p-2 glass-panel rounded-lg cursor-pointer hover:bg-slate-700/50 transition-colors"
                            >
                                <input
                                    type="checkbox"
                                    checked={selectedRecipients.includes(recipient.id)}
                                    onChange={() => toggleRecipient(recipient.id)}
                                    className="w-4 h-4"
                                />
                                <span className="text-sm">{recipient.name}</span>
                            </label>
                        ))
                    )}
                </div>
            </div>

            {/* Channel Selection */}
            <div>
                <h3 className="text-sm font-semibold mb-3 text-slate-300">Select Channels</h3>
                <div className="space-y-2">
                    <label
                        className={`flex items-center gap-3 p-3 glass-panel rounded-lg cursor-pointer transition-all ${serviceStatus?.whatsapp ? 'hover:bg-slate-700/50' : 'opacity-50 cursor-not-allowed'
                            }`}
                    >
                        <input
                            type="checkbox"
                            checked={selectedChannels.includes('whatsapp')}
                            onChange={() => toggleChannel('whatsapp')}
                            disabled={!serviceStatus?.whatsapp}
                            className="w-4 h-4"
                        />
                        <MessageSquare className="w-4 h-4 text-green-500" />
                        <span className="text-sm">WhatsApp</span>
                        {!serviceStatus?.whatsapp && (
                            <span className="ml-auto text-xs text-red-400">Not configured</span>
                        )}
                    </label>

                    <label
                        className={`flex items-center gap-3 p-3 glass-panel rounded-lg cursor-pointer transition-all ${serviceStatus?.sms ? 'hover:bg-slate-700/50' : 'opacity-50 cursor-not-allowed'
                            }`}
                    >
                        <input
                            type="checkbox"
                            checked={selectedChannels.includes('sms')}
                            onChange={() => toggleChannel('sms')}
                            disabled={!serviceStatus?.sms}
                            className="w-4 h-4"
                        />
                        <Smartphone className="w-4 h-4 text-blue-500" />
                        <span className="text-sm">SMS</span>
                        {!serviceStatus?.sms && (
                            <span className="ml-auto text-xs text-red-400">Not configured</span>
                        )}
                    </label>

                    <label
                        className={`flex items-center gap-3 p-3 glass-panel rounded-lg cursor-pointer transition-all ${serviceStatus?.email ? 'hover:bg-slate-700/50' : 'opacity-50 cursor-not-allowed'
                            }`}
                    >
                        <input
                            type="checkbox"
                            checked={selectedChannels.includes('email')}
                            onChange={() => toggleChannel('email')}
                            disabled={!serviceStatus?.email}
                            className="w-4 h-4"
                        />
                        <Mail className="w-4 h-4 text-purple-500" />
                        <span className="text-sm">Email</span>
                        {!serviceStatus?.email && (
                            <span className="ml-auto text-xs text-red-400">Not configured</span>
                        )}
                    </label>
                </div>
            </div>

            {/* Custom Message */}
            <div>
                <h3 className="text-sm font-semibold mb-3 text-slate-300">Custom Message (Optional)</h3>
                <textarea
                    value={customMessage}
                    onChange={e => setCustomMessage(e.target.value)}
                    placeholder="Add a custom message to include in the alert..."
                    rows={3}
                    className="w-full px-4 py-2 bg-slate-800/50 border border-border rounded-lg focus:outline-none focus:border-primary-500 text-sm resize-none"
                />
            </div>

            {/* Send Button */}
            <Button
                variant="primary"
                size="lg"
                onClick={handleSend}
                loading={sending}
                disabled={sending || selectedDetections.length === 0 || selectedRecipients.length === 0 || selectedChannels.length === 0}
                icon={sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                className="w-full"
            >
                {progress || 'Send Alerts'}
            </Button>
        </div>
    )
}
