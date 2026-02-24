import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Sanad AI — سند',
  description: 'مستشار قانوني ذكي متخصص في الأنظمة السعودية: الأحوال الشخصية والإثبات والمرافعات الشرعية',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body className="min-h-screen bg-gray-50">
        {children}
      </body>
    </html>
  );
}
