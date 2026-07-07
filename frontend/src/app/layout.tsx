import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AutoMTO | Piping Isometric AI Extractor",
  description: "Industry-grade full-stack piping engineering MTO generator using Vision AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {/* Background grids and glowing ambient lights */}
        <div className="bg-decorations">
          <div className="grid-overlay" />
        </div>

        {/* Premium Header */}
        <header style={{
          padding: '1rem 2rem',
          borderBottom: 'var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(255, 255, 255, 0.7)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          boxShadow: '0 4px 20px rgba(15, 23, 42, 0.03)'
        }}>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', outline: 'none' }} className="brand-link">
            <div style={{
              width: '36px',
              height: '36px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(79, 70, 229, 0.04)',
              border: '1px solid rgba(79, 70, 229, 0.15)',
              borderRadius: '10px',
              boxShadow: '0 4px 12px rgba(15, 23, 42, 0.02)'
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="url(#cube-top)" />
                <path d="M2 7V17L12 22V12L2 7Z" fill="url(#cube-left)" />
                <path d="M12 12V22L22 17V7L12 12Z" fill="url(#cube-right)" />
                <defs>
                  <linearGradient id="cube-top" x1="12" y1="2" x2="12" y2="12" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#818cf8" />
                    <stop offset="1" stopColor="#6366f1" />
                  </linearGradient>
                  <linearGradient id="cube-left" x1="2" y1="7" x2="12" y2="22" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#4f46e5" />
                    <stop offset="1" stopColor="#312e81" />
                  </linearGradient>
                  <linearGradient id="cube-right" x1="12" y1="12" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#6366f1" />
                    <stop offset="1" stopColor="#4338ca" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '1.1rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--foreground)', lineHeight: 1.1 }}>AutoMTO</span>
              <span style={{ fontSize: '0.65rem', fontWeight: 600, letterSpacing: '0.05em', color: 'var(--color-secondary-500)', textTransform: 'uppercase' }}>Piping Workspace</span>
            </div>
          </Link>

          <nav style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
            <span style={{
              fontSize: '0.75rem',
              color: 'var(--color-success)',
              background: 'var(--color-success-bg)',
              border: '1px solid rgba(5, 150, 105, 0.2)',
              padding: '0.25rem 0.6rem',
              borderRadius: '9999px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem'
            }}>
              <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--color-success)', borderRadius: '50%', display: 'inline-block', animation: 'pulse 2s infinite' }}></span>
              AI Core Online
            </span>
          </nav>
        </header>

        {/* Main Workspace Viewport */}
        <main style={{ flex: 1, padding: '2rem 1rem', display: 'flex', flexDirection: 'column' }}>
          {children}
        </main>

        {/* Footer */}
        <footer style={{
          padding: '2rem',
          borderTop: 'var(--border-subtle)',
          background: 'rgba(255, 255, 255, 0.7)',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.8rem',
          color: 'var(--color-secondary-500)'
        }}>
          <div>
            <strong style={{ color: 'var(--color-secondary-900)' }}>AutoMTO</strong> · Automated Material Take-Off Engine
          </div>
          <div>
            Conforms to ASME B31.3 Piping Design Code, ASME B16.5 Flanges & B16.9 Fittings Standards.
          </div>
          <div style={{ marginTop: '0.5rem', display: 'flex', gap: '1rem', color: 'var(--color-secondary-500)' }}>
            <span>WCAG 2.1 AA Compliant</span>
            <span>·</span>
            <span>Vision-Language Model Extraction</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
