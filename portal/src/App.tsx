import { useState, useEffect } from 'react'
import { MapPin, FileAudio, Languages, BookOpen, Sun, Moon } from 'lucide-react'

export default function App() {
    const [isDark, setIsDark] = useState(true)

    useEffect(() => {
        // Initialize dark mode from localStorage or default to dark
        const stored = localStorage.getItem('lmsilo-theme')
        const prefersDark = stored === 'dark' || (!stored && true)
        setIsDark(prefersDark)
        document.documentElement.classList.toggle('dark', prefersDark)
    }, [])

    const toggleTheme = () => {
        const newIsDark = !isDark
        setIsDark(newIsDark)
        document.documentElement.classList.toggle('dark', newIsDark)
        localStorage.setItem('lmsilo-theme', newIsDark ? 'dark' : 'light')
    }

    return (
        <div className="min-h-screen bg-cream-100 transition-colors duration-300">
            {/* Header */}
            <header className="border-b border-cream-200 bg-white transition-colors duration-300">
                <div className="max-w-6xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <h1 className="text-3xl font-serif text-surface-800">LMSilo</h1>
                        <button
                            onClick={toggleTheme}
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
            </header>

            {/* Main content */}
            <main className="max-w-6xl mx-auto px-6 py-16">
                <div className="text-center mb-16 animate-fade-in">
                    <h2 className="text-4xl font-serif text-surface-800 mb-4">
                        Local AI Suite
                    </h2>
                    <p className="text-lg text-surface-500 max-w-2xl mx-auto">
                        Privacy-first AI tools running entirely on your infrastructure.
                        No data leaves your network.
                    </p>
                </div>

                {/* Tool cards */}
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 animate-fade-in" style={{ animationDelay: '0.1s' }}>
                    {/* Locate Card */}
                    <a
                        href="http://localhost:8081"
                        className="tool-card group block"
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
                                    AI-powered image geolocation using GeoCLIP
                                </p>
                            </div>
                        </div>
                    </a>

                    {/* Transcribe Card */}
                    <a
                        href="http://localhost:8082"
                        className="tool-card group block"
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
                                    Speech-to-text with speaker diarization
                                </p>
                            </div>
                        </div>
                    </a>

                    {/* Translate Card */}
                    <a
                        href="http://localhost:8083"
                        className="tool-card group block"
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
                        className="tool-card group block"
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
        </div>
    )
}
