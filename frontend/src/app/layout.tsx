import type { Metadata } from 'next';
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
        {children}
      </body>
    </html>
  );
}
