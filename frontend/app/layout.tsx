import type { Metadata, Viewport } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'المستشار القانوني الذكي',
  description: 'مساعد قانوني ذكي متخصص في الأنظمة السعودية: الأحوال الشخصية والإثبات والمرافعات الشرعية',
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
        <div className="flex min-h-screen">
          <Sidebar />
          {/* pt-14 on mobile for top bar, lg:pt-0 on desktop; mr-0 on mobile, lg:mr-64 for sidebar */}
          <main className="flex-1 mr-0 lg:mr-64 pt-14 lg:pt-0">{children}</main>
        </div>
      </body>
    </html>
  );
}
