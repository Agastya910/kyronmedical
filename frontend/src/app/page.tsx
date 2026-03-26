import { ChatInterface } from '@/components/ChatInterface';

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden" style={{ background: 'var(--kyron-navy)' }}>
      {/* Animated background orbs */}
      <div className="bg-orb bg-orb-1" />
      <div className="bg-orb bg-orb-2" />
      <div className="bg-orb bg-orb-3" />

      {/* SVG Refraction filter for glass depth effect */}
      <svg className="absolute w-0 h-0">
        <defs>
          <filter id="liquid-glass-filter">
            <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="blur" />
            <feDisplacementMap in="SourceGraphic" in2="blur" scale="6"
              xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>
      </svg>

      {/* Hero Section */}
      <div className="relative z-20 pt-16 pb-8 px-6 max-w-4xl mx-auto text-center">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight drop-shadow-md">
          Kyron Care — AI-Powered Patient Services
        </h1>
        <p className="text-xl text-white/80 mb-8 max-w-2xl mx-auto">
          Schedule appointments, refill prescriptions, and get answers — 24/7, in chat or by phone.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <span className="backdrop-blur-md bg-white/10 border border-white/20 rounded-full px-4 py-1.5 text-blue-400 font-medium text-sm">
            4 Specialists
          </span>
          <span className="backdrop-blur-md bg-white/10 border border-white/20 rounded-full px-4 py-1.5 text-blue-400 font-medium text-sm">
            24/7 Available
          </span>
        </div>
      </div>

      {/* Chat Interface */}
      <div className="relative z-10 h-[calc(100vh-280px)] min-h-[500px]">
        <ChatInterface />
      </div>
    </main>
  );
}
