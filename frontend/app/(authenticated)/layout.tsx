'use client';

import { AuthProvider } from '@/lib/supabase/auth-context';
import { SubscriptionProvider } from '@/lib/supabase/subscription-context';
import Sidebar from '@/components/Sidebar';

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <SubscriptionProvider>
        <div className="flex min-h-screen bg-surface-50">
          <Sidebar />
          <main className="flex-1 mr-0 lg:mr-72 pt-14 lg:pt-0">
            {children}
          </main>
        </div>
      </SubscriptionProvider>
    </AuthProvider>
  );
}
