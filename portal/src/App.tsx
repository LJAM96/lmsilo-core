import { useState, useEffect } from 'react'
import { MapPin, FileAudio, Languages, BookOpen, Sun, Moon, Settings, X } from 'lucide-react'
import { useTheme } from '@lmsilo/shared-ui'

// Declare global config type
declare global {
    interface Window {
        __LMSILO_CONFIG__?: {
            PORTAL_TICKER?: string
        }
    }
}

export default function App() {
    const { isDark, toggle } = useTheme()
    const [ticker, setTicker] = useState('')
    const [showSettings, setShowSettings] = useState(false)

    useEffect(() => {
        // Get ticker from runtime config
        const config = window.__LMSILO_CONFIG__
        if (config?.PORTAL_TICKER) {
            setTicker(config.PORTAL_TICKER)
        }
    }, [])

    return (
        <div className="min-h-screen bg-cream-100 dark:bg-dark-500 transition-colors duration-300 flex flex-col">
            {/* Header */}
            <header className="border-b border-cream-200 bg-white dark:bg-surface-800 transition-all duration-300">
                <div className="max-w-6xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <h1 className="text-3xl font-serif text-surface-800 dark:text-cream-100">LMSilo</h1>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setShowSettings(true)}
                                className="p-2 rounded-xl bg-cream-200 hover:bg-cream-300 transition-colors"
                                aria-label="Settings"
                            >
                                <Settings className="w-5 h-5 text-surface-600" />
                            </button>
                            <button
                                onClick={toggle}
                                className="p-2 rounded-xl bg-cream-200 hover:bg-cream-300 transition-colors"
                                aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                            >
                                {isDark ? (
                                    <Sun className="w-5 h-5 text-cream-400" />
                                ) : (
                                    <Moon className="w-5 h-5 text-surface-600" />
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
                {/* News Ticker */}
                {ticker && (
                    <div className="mb-8 overflow-hidden rounded-xl bg-white dark:bg-surface-800 shadow-soft border border-cream-200 dark:border-surface-700 p-3 flex items-center gap-3">
                         <div className="bg-olive-100 dark:bg-olive-900/30 text-olive-700 dark:text-olive-300 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider shrink-0">
                            News
                        </div>
                        <div className="ticker-container overflow-hidden whitespace-nowrap mask-linear flex-1">
                            <div className="ticker-content inline-block">
                                <span className="ticker-text text-surface-600 dark:text-surface-300">{ticker}</span>
                                <span className="ticker-spacer"> • </span>
                                <span className="ticker-text text-surface-600 dark:text-surface-300">{ticker}</span>
                                <span className="ticker-spacer"> • </span>
                                <span className="ticker-text text-surface-600 dark:text-surface-300">{ticker}</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Hero Section */}
                <div className="text-center mb-16 space-y-4">
                    <h2 className="text-4xl md:text-5xl font-serif text-surface-800 dark:text-cream-100">
                        Local AI Suite
                    </h2>
                    <p className="text-xl text-surface-500 dark:text-surface-400 max-w-2xl mx-auto leading-relaxed">
                        Powerful offline AI tools for privacy-first productivity
                    </p>
                </div>

                {/* Tools Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {/* Locate Card */}
                    <a
                        href="http://localhost:5174"
                        className="card group block hover:border-olive-300 transition-all duration-300 hover:shadow-medium hover:scale-[1.02] cursor-pointer"
                    >
                        <div className="flex flex-col items-center text-center gap-4">
                            <div className="w-16 h-16 bg-olive-600 rounded-2xl flex items-center justify-center group-hover:bg-olive-700 transition-colors">
                                <MapPin className="w-8 h-8 text-white" />
                            </div>
                            <div>
                                <h3 className="text-2xl font-serif text-surface-800 mb-2">
                                    Locate
                                </h3>
                                <p className="text-surface-500 text-sm leading-relaxed">
                                    Privacy-preserving image geolocation
                                </p>
                            </div>
                        </div>
                    </a>

                    {/* Speech Card */}
                    <a
                        href="http://localhost:5176"
                        className="card group block hover:border-olive-300 transition-all duration-300 hover:shadow-medium hover:scale-[1.02] cursor-pointer"
                    >
                        <div className="flex flex-col items-center text-center gap-4">
                            <div className="w-16 h-16 bg-olive-600 rounded-2xl flex items-center justify-center group-hover:bg-olive-700 transition-colors">
                                <FileAudio className="w-8 h-8 text-white" />
                            </div>
                            <div>
                                <h3 className="text-2xl font-serif text-surface-800 mb-2">
                                    Transcribe
                                </h3>
                                <p className="text-surface-500 text-sm leading-relaxed">
                                    Offline speech-to-text transcription
                                </p>
                            </div>
                        </div>
                    </a>

                    {/* Translate Card */}
                    <a
                        href="http://localhost:5175"
                        className="card group block hover:border-olive-300 transition-all duration-300 hover:shadow-medium hover:scale-[1.02] cursor-pointer"
                    >
                        <div className="flex flex-col items-center text-center gap-4">
                            <div className="w-16 h-16 bg-olive-600 rounded-2xl flex items-center justify-center group-hover:bg-olive-700 transition-colors">
                                <Languages className="w-8 h-8 text-white" />
                            </div>
                            <div>
                                <h3 className="text-2xl font-serif text-surface-800 mb-2">
                                    Translate
                                </h3>
                                <p className="text-surface-500 text-sm leading-relaxed">
                                    AI translation powered by NLLB-200
                                </p>
                            </div>
                        </div>
                    </a>

                    {/* Wiki Card */}
                    <a
                        href="http://localhost:88"
                        className="card group block hover:border-olive-300 transition-all duration-300 hover:shadow-medium hover:scale-[1.02] cursor-pointer"
                    >
                        <div className="flex flex-col items-center text-center gap-4">
                            <div className="w-16 h-16 bg-olive-600 rounded-2xl flex items-center justify-center group-hover:bg-olive-700 transition-colors">
                                <BookOpen className="w-8 h-8 text-white" />
                            </div>
                            <div>
                                <h3 className="text-2xl font-serif text-surface-800 mb-2">
                                    Wiki
                                </h3>
                                <p className="text-surface-500 text-sm leading-relaxed">
                                    Documentation and knowledge base
                                </p>
                            </div>
                        </div>
                    </a>
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-cream-200 mt-auto">
                <div className="max-w-6xl mx-auto px-6 py-6 text-center text-sm text-surface-500">
                    <p>LMSilo • Local AI Suite</p>
                </div>
            </footer>

            {/* Settings Modal */}
            {showSettings && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowSettings(false)}>
                    <div 
                        className="bg-white dark:bg-surface-800 rounded-2xl shadow-xl max-w-md w-full mx-4 overflow-hidden"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between p-6 border-b border-cream-200 dark:border-surface-700">
                            <h2 className="text-xl font-serif text-surface-800 dark:text-cream-100">Settings</h2>
                            <button
                                onClick={() => setShowSettings(false)}
                                className="p-2 rounded-lg hover:bg-cream-100 dark:hover:bg-surface-700 transition-colors"
                            >
                                <X className="w-5 h-5 text-surface-500" />
                            </button>
                        </div>
                        <div className="p-6 space-y-6">
                            {/* Dark Mode Toggle */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="font-medium text-surface-700 dark:text-cream-200">Dark mode</p>
                                    <p className="text-sm text-surface-500 dark:text-surface-400">
                                        Use dark theme for the interface
                                    </p>
                                </div>
                                <button
                                    onClick={toggle}
                                    className={`
                                        relative w-12 h-6 rounded-full transition-colors
                                        ${isDark ? 'bg-olive-600' : 'bg-surface-300'}
                                    `}
                                >
                                    <span
                                        className={`
                                            absolute top-1 left-1 w-4 h-4 rounded-full bg-white
                                            transition-transform
                                            ${isDark ? 'translate-x-6' : 'translate-x-0'}
                                        `}
                                    />
                                </button>
                            </div>
                        </div>
                        <div className="p-6 bg-cream-50 dark:bg-surface-900 border-t border-cream-200 dark:border-surface-700">
                            <p className="text-xs text-surface-500 text-center">
                                LMSilo • Local AI Suite • v1.0.0
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

