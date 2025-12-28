'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'

type Theme = 'light' | 'dark' | 'system'

interface SettingsContextType {
    theme: Theme
    setTheme: (theme: Theme) => void
    enableAnimations: boolean
    setEnableAnimations: (enable: boolean) => void
    enableTexture: boolean
    setEnableTexture: (enable: boolean) => void
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

export function SettingsProvider({ children }: { children: React.ReactNode }) {
    const [theme, setThemeState] = useState<Theme>('dark')
    const [enableAnimations, setEnableAnimationsState] = useState(true)
    const [enableTexture, setEnableTextureState] = useState(true)
    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        // Load from localStorage on mount
        const storedTheme = localStorage.getItem('theme') as Theme
        const storedAnims = localStorage.getItem('enableAnimations')
        const storedTexture = localStorage.getItem('enableTexture')

        if (storedTheme) setThemeState(storedTheme)
        if (storedAnims !== null) setEnableAnimationsState(JSON.parse(storedAnims))
        if (storedTexture !== null) setEnableTextureState(JSON.parse(storedTexture))

        setMounted(true)
    }, [])

    useEffect(() => {
        if (!mounted) return
        localStorage.setItem('theme', theme)

        // Apply theme class
        const root = document.documentElement
        root.classList.remove('light', 'dark')

        if (theme === 'system') {
            const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
            root.classList.add(systemTheme)
        } else {
            root.classList.add(theme)
        }
    }, [theme, mounted])

    useEffect(() => {
        if (!mounted) return
        localStorage.setItem('enableAnimations', JSON.stringify(enableAnimations))
    }, [enableAnimations, mounted])

    useEffect(() => {
        if (!mounted) return
        localStorage.setItem('enableTexture', JSON.stringify(enableTexture))
    }, [enableTexture, mounted])

    const setTheme = (newTheme: Theme) => {
        setThemeState(newTheme)
    }

    const setEnableAnimations = (enable: boolean) => {
        setEnableAnimationsState(enable)
    }

    const setEnableTexture = (enable: boolean) => {
        setEnableTextureState(enable)
    }

    // We always render the provider with default values to avoid context errors.
    // The useEffects will handle syncing with localStorage/DOM after mount.

    return (
        <SettingsContext.Provider value={{ theme, setTheme, enableAnimations, setEnableAnimations, enableTexture, setEnableTexture }}>
            {children}
        </SettingsContext.Provider>
    )
}

export function useSettings() {
    const context = useContext(SettingsContext)
    if (context === undefined) {
        throw new Error('useSettings must be used within a SettingsProvider')
    }
    return context
}
