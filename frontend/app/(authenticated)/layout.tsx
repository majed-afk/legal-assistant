'use client';

import { AuthProvider } from '@/lib/supabase/auth-context';
import { SubscriptionProvider } from '@/lib/supabase/subscription-context';
import { ThemeProvider } from '@/lib/theme-context';
import ErrorBoundary from '@/components/ErrorBoundary';
import Sidebar from '@/components/Sidebar';
import NetworkStatus from '@/components/NetworkStatus';

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <SubscriptionProvider>
          <ThemeProvider>
            <NetworkStatus />
            <div className="flex min-h-screen bg-surface-50 dark:bg-surface-900 transition-colors duration-300">
              <Sidebar />
              <main className="flex-1 mr-0 lg:mr-72 pt-14 lg:pt-0">
                {children}
              </main>
            </div>
          </ThemeProvider>
        </SubscriptionProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
