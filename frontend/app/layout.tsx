import type { Metadata, Viewport } from 'next';
import './globals.css';

const SITE_URL = 'https://sanad.audience.sa';

export const metadata: Metadata = {
  title: {
    default: 'Sanad AI — سند | مستشارك القانوني الذكي',
    template: '%s | سند',
  },
  description: 'مستشار قانوني ذكي متخصص في الأنظمة السعودية: الأحوال الشخصية والمعاملات المدنية والإثبات والمرافعات الشرعية والمحاكم التجارية. احصل على استشارات قانونية فورية مدعومة بالذكاء الاصطناعي.',
  manifest: '/manifest.json',
  metadataBase: new URL(SITE_URL),
  openGraph: {
    type: 'website',
    locale: 'ar_SA',
    url: SITE_URL,
    siteName: 'Sanad AI — سند',
    title: 'سند — مستشارك القانوني الذكي',
    description: 'احصل على استشارات قانونية فورية في الأحوال الشخصية والمعاملات المدنية والإثبات والمرافعات الشرعية',
    images: [{ url: '/icons/icon-512x512.png', width: 512, height: 512, alt: 'سند - مستشار قانوني ذكي' }],
  },
  twitter: {
    card: 'summary',
    title: 'سند — مستشارك القانوني الذكي',
    description: 'استشارات قانونية فورية مدعومة بالذكاء الاصطناعي — متخصص في 5 أنظمة سعودية',
    images: ['/icons/icon-512x512.png'],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'سند',
  },
  icons: {
    icon: [
      { url: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [
      { url: '/icons/icon-152x152.png', sizes: '152x152', type: 'image/png' },
      { url: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
    ],
  },
  keywords: ['مستشار قانوني', 'أحوال شخصية', 'معاملات مدنية', 'إثبات', 'مرافعات شرعية', 'قانون سعودي', 'ذكاء اصطناعي', 'سند'],
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#0f172a',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebApplication',
    name: 'Sanad AI — سند',
    description: 'مستشار قانوني ذكي متخصص في الأنظمة السعودية',
    url: SITE_URL,
    applicationCategory: 'LegalService',
    operatingSystem: 'Web',
    inLanguage: 'ar',
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'SAR' },
    provider: { '@type': 'Organization', name: 'Sanad AI', url: SITE_URL },
  };

  return (
    <html lang="ar" dir="rtl" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&family=Noto+Naskh+Arabic:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="mobile-web-app-capable" content="yes" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem('sanad-theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})()` }} />
      </head>
      <body className="min-h-screen bg-surface-50 dark:bg-surface-900 font-sans antialiased transition-colors duration-300">
        {children}
      </body>
    </html>
  );
}
