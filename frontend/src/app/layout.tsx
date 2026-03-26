import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'Kyron Care — Patient Scheduling',
  description: 'Schedule appointments with Kyron Medical Group. Fast, intelligent, and always available.',
  icons: { icon: '/favicon.ico' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <nav className="sticky top-0 z-50 backdrop-blur-md bg-white/10 border-b border-white/20">
          <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
            <Link href="/" className="text-xl font-bold text-white tracking-wide">
              Kyron Care
            </Link>
            <div className="flex gap-6">
              <Link href="/" className="text-white/70 hover:text-white transition-colors">Home</Link>
              <Link href="/doctors" className="text-white/70 hover:text-white transition-colors">Our Doctors</Link>
              <Link href="/services" className="text-white/70 hover:text-white transition-colors">Our Services</Link>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
