'use client'

import { useState } from 'react'
import { Plus, Trash2, Edit2, Phone, Mail, CheckCircle, XCircle } from 'lucide-react'
import { AlertRecipient } from '@/types'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { apiClient } from '@/lib/api-client'

interface RecipientManagerProps {
    recipients: AlertRecipient[]
    onRecipientChange: () => void
}

export function RecipientManager({ recipients, onRecipientChange }: RecipientManagerProps) {
    const [showAddModal, setShowAddModal] = useState(false)
    const [editingRecipient, setEditingRecipient] = useState<AlertRecipient | null>(null)
    const [formData, setFormData] = useState({
        name: '',
        phone: '',
        email: '',
        preferredChannels: [] as ('whatsapp' | 'sms' | 'email')[],
        active: true,
    })
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleAdd = () => {
        setFormData({
            name: '',
            phone: '',
            email: '',
            preferredChannels: [],
            active: true,
        })
        setEditingRecipient(null)
        setShowAddModal(true)
        setError(null)
    }

    const handleEdit = (recipient: AlertRecipient) => {
        setFormData({
            name: recipient.name,
            phone: recipient.phone || '',
            email: recipient.email || '',
            preferredChannels: recipient.preferredChannels,
            active: recipient.active,
        })
        setEditingRecipient(recipient)
        setShowAddModal(true)
        setError(null)
    }

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to delete this recipient?')) return

        try {
            await apiClient.delete(`/api/alerts/recipients?id=${id}`)
            onRecipientChange()
        } catch (err) {
            alert('Failed to delete recipient')
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setSubmitting(true)
        setError(null)

        try {
            if (editingRecipient) {
                await apiClient.put('/api/alerts/recipients', {
                    id: editingRecipient.id,
                    ...formData,
                })
            } else {
                await apiClient.post('/api/alerts/recipients', formData)
            }

            setShowAddModal(false)
            onRecipientChange()
        } catch (err: any) {
            setError(err.message || 'Failed to save recipient')
        } finally {
            setSubmitting(false)
        }
    }

    const toggleChannel = (channel: 'whatsapp' | 'sms' | 'email') => {
        setFormData(prev => ({
            ...prev,
            preferredChannels: prev.preferredChannels.includes(channel)
                ? prev.preferredChannels.filter(c => c !== channel)
                : [...prev.preferredChannels, channel],
        }))
    }

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-border">
                <Button
                    variant="primary"
                    size="sm"
                    icon={<Plus className="w-4 h-4" />}
                    onClick={handleAdd}
                    className="w-full"
                >
                    Add Recipient
                </Button>
            </div>

            {/* Recipient List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {recipients.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-slate-500 mb-4">No recipients added yet</p>
                        <Button variant="outline" size="sm" onClick={handleAdd}>
                            Add Your First Recipient
                        </Button>
                    </div>
                ) : (
                    recipients.map(recipient => (
                        <div
                            key={recipient.id}
                            className="glass-panel p-4 rounded-lg border border-border hover:border-primary-500/50 transition-all"
                        >
                            <div className="flex items-start justify-between mb-2">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        <h3 className="font-semibold text-foreground">{recipient.name}</h3>
                                        {recipient.active ? (
                                            <CheckCircle className="w-4 h-4 text-green-500" />
                                        ) : (
                                            <XCircle className="w-4 h-4 text-red-500" />
                                        )}
                                    </div>
                                    <div className="flex flex-col gap-1 text-sm text-slate-500">
                                        {recipient.phone && (
                                            <div className="flex items-center gap-2">
                                                <Phone className="w-3 h-3" />
                                                <span>{recipient.phone}</span>
                                            </div>
                                        )}
                                        {recipient.email && (
                                            <div className="flex items-center gap-2">
                                                <Mail className="w-3 h-3" />
                                                <span>{recipient.email}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => handleEdit(recipient)}
                                        className="p-2 hover:bg-slate-700/50 rounded transition-colors"
                                    >
                                        <Edit2 className="w-4 h-4 text-slate-400" />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(recipient.id)}
                                        className="p-2 hover:bg-red-900/30 rounded transition-colors"
                                    >
                                        <Trash2 className="w-4 h-4 text-red-400" />
                                    </button>
                                </div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {recipient.preferredChannels.map(channel => (
                                    <Badge key={channel} variant="default" size="sm">
                                        {channel}
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Add/Edit Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="glass-panel max-w-md w-full rounded-xl border border-border p-6">
                        <h2 className="text-xl font-bold mb-4">
                            {editingRecipient ? 'Edit Recipient' : 'Add Recipient'}
                        </h2>

                        {error && (
                            <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-3 rounded-lg mb-4 text-sm">
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Name *</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-4 py-2 bg-slate-800/50 border border-border rounded-lg focus:outline-none focus:border-primary-500"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Phone Number</label>
                                <input
                                    type="tel"
                                    value={formData.phone}
                                    onChange={e => setFormData({ ...formData, phone: e.target.value })}
                                    placeholder="+1234567890"
                                    className="w-full px-4 py-2 bg-slate-800/50 border border-border rounded-lg focus:outline-none focus:border-primary-500"
                                />
                                <p className="text-xs text-slate-500 mt-1">Required for WhatsApp/SMS</p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Email</label>
                                <input
                                    type="email"
                                    value={formData.email}
                                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                                    placeholder="user@example.com"
                                    className="w-full px-4 py-2 bg-slate-800/50 border border-border rounded-lg focus:outline-none focus:border-primary-500"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-3">Preferred Channels *</label>
                                <div className="space-y-2">
                                    {['whatsapp', 'sms', 'email'].map(channel => (
                                        <label key={channel} className="flex items-center gap-3 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={formData.preferredChannels.includes(channel as any)}
                                                onChange={() => toggleChannel(channel as any)}
                                                className="w-4 h-4"
                                            />
                                            <span className="capitalize">{channel}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div className="flex items-center gap-3">
                                <input
                                    type="checkbox"
                                    id="active"
                                    checked={formData.active}
                                    onChange={e => setFormData({ ...formData, active: e.target.checked })}
                                    className="w-4 h-4"
                                />
                                <label htmlFor="active" className="text-sm font-medium cursor-pointer">
                                    Active
                                </label>
                            </div>

                            <div className="flex gap-3 pt-4">
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => setShowAddModal(false)}
                                    className="flex-1"
                                    disabled={submitting}
                                >
                                    Cancel
                                </Button>
                                <Button type="submit" variant="primary" className="flex-1" loading={submitting}>
                                    {editingRecipient ? 'Update' : 'Add'}
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
