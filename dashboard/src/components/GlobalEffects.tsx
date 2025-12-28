'use client'

import { useSettings } from '@/context/SettingsContext'
import { UnicornBackground } from '@/components/UnicornBackground'
import { SpotlightEffect } from '@/components/SpotlightEffect'

export function GlobalEffects() {
    const { enableAnimations, enableTexture } = useSettings()

    return (
        <>
            {enableAnimations && <UnicornBackground />}
            {enableTexture && <div className="noise-overlay"></div>}
            {enableAnimations && <SpotlightEffect />}
        </>
    )
}
