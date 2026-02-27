'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { verifyPayment } from '@/lib/api';
import { useSubscription } from '@/lib/supabase/subscription-context';

function CallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { refreshSubscription, refreshUsage } = useSubscription();
  const [status, setStatus] = useState<'verifying' | 'success' | 'failed'>('verifying');
  const [message, setMessage] = useState('جاري التحقق من عملية الدفع...');

  useEffect(() => {
    const paymentId = searchParams.get('id') || searchParams.get('payment_id');
    const txId = searchParams.get('tx_id');

    if (!paymentId) {
      setStatus('failed');
      setMessage('لم يتم العثور على معرّف الدفع');
      return;
    }

    verifyPayment(paymentId, txId || undefined)
      .then(async (result) => {
        if (result.status === 'paid') {
          setStatus('success');
          setMessage(result.message || 'تم تفعيل الاشتراك بنجاح!');
          await refreshSubscription();
          await refreshUsage();
          setTimeout(() => router.push('/subscription'), 3000);
        } else {
          setStatus('failed');
          setMessage(result.message || 'فشلت عملية الدفع');
        }
      })
      .catch((e) => {
        setStatus('failed');
        setMessage(e.message || 'حدث خطأ أثناء التحقق');
      });
  }, [searchParams, router, refreshSubscription, refreshUsage]);

  return (
    <div className="max-w-md w-full bg-white rounded-2xl border border-gray-200 p-8 text-center shadow-lg">
      {/* Status icon */}
      <div className="mb-6">
        {status === 'verifying' && (
          <div className="w-16 h-16 mx-auto rounded-full bg-primary-50 flex items-center justify-center">
            <div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {status === 'success' && (
          <div className="w-16 h-16 mx-auto rounded-full bg-green-50 flex items-center justify-center animate-fade-in">
            <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
        {status === 'failed' && (
          <div className="w-16 h-16 mx-auto rounded-full bg-red-50 flex items-center justify-center animate-fade-in">
            <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        )}
      </div>

      {/* Message */}
      <h2 className="text-xl font-bold text-gray-900 mb-2">
        {status === 'verifying' ? 'جاري التحقق' : status === 'success' ? 'تم بنجاح!' : 'فشلت العملية'}
      </h2>
      <p className="text-gray-600 text-sm mb-6">{message}</p>

      {/* Actions */}
      {status === 'success' && (
        <p className="text-xs text-gray-400">سيتم تحويلك تلقائياً خلال 3 ثوانٍ...</p>
      )}
      {status === 'failed' && (
        <div className="flex gap-3">
          <button
            onClick={() => router.push('/subscription')}
            className="flex-1 py-2.5 rounded-xl bg-primary-500 text-white font-medium text-sm hover:bg-primary-600 transition-colors"
          >
            حاول مرة أخرى
          </button>
          <button
            onClick={() => router.push('/chat')}
            className="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-700 font-medium text-sm hover:bg-gray-200 transition-colors"
          >
            العودة للمحادثة
          </button>
        </div>
      )}
    </div>
  );
}

export default function PaymentCallbackPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4" dir="rtl">
      <Suspense
        fallback={
          <div className="max-w-md w-full bg-white rounded-2xl border border-gray-200 p-8 text-center shadow-lg">
            <div className="w-16 h-16 mx-auto rounded-full bg-primary-50 flex items-center justify-center mb-6">
              <div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">جاري التحقق</h2>
            <p className="text-gray-600 text-sm">جاري التحقق من عملية الدفع...</p>
          </div>
        }
      >
        <CallbackContent />
      </Suspense>
    </div>
  );
}
