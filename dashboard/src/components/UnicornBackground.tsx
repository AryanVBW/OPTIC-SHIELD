'use client'

import Script from 'next/script'

export function UnicornBackground() {
    return (
        <div
            className="aura-background-component fixed top-0 w-full h-screen -z-10 pointer-events-none"
            data-alpha-mask="80"
            style={{
                opacity: 0.4
            }}
        >
            <div className="aura-background-component top-0 w-full -z-10 absolute h-full">
                <div data-us-project="NMlvqnkICwYYJ6lYb064" className="absolute w-full h-full left-0 top-0 -z-10"></div>
                <Script
                    src="https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v1.4.29/dist/unicornStudio.umd.js"
                    strategy="lazyOnload"
                    onLoad={() => {
                        // @ts-ignore
                        if (!window.UnicornStudio) {
                            // @ts-ignore
                            window.UnicornStudio = { isInitialized: false };
                        }
                        // @ts-ignore
                        if (!window.UnicornStudio.isInitialized) {
                            // @ts-ignore
                            UnicornStudio.init();
                            // @ts-ignore
                            window.UnicornStudio.isInitialized = true;
                        }
                    }}
                />
            </div>
        </div>
    )
}
