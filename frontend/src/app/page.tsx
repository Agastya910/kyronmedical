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

      {/* Chat Interface */}
      <div className="relative z-10 h-screen">
        <ChatInterface />
      </div>
    </main>
  );
}
