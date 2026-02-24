import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'سياسة الخصوصية — Sanad AI',
  description: 'سياسة الخصوصية لتطبيق سند - مستشارك القانوني الذكي',
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-surface-950 text-gray-200" dir="rtl">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-surface-950/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-primary-400 hover:text-primary-300 transition-colors text-sm font-medium"
          >
            <svg className="w-4 h-4 rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            العودة للرئيسية
          </Link>
          <span className="text-sm text-gray-500">Sanad AI</span>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-6 py-12">
        {/* Title */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-lg mb-5">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-white font-heading mb-3">سياسة الخصوصية</h1>
          <p className="text-gray-400 text-sm">
            آخر تحديث: ٢٤ فبراير ٢٠٢٦
          </p>
        </div>

        {/* Introduction */}
        <div className="bg-white/[0.04] backdrop-blur-sm border border-white/5 rounded-2xl p-6 mb-8">
          <p className="text-gray-300 leading-relaxed text-sm">
            مرحبا بكم في تطبيق <strong className="text-white">سند (Sanad AI)</strong>، المستشار القانوني الذكي المتخصص في الأنظمة السعودية.
            نحن نقدّر خصوصيتكم ونلتزم بحماية بياناتكم الشخصية. توضّح هذه السياسة كيفية جمع بياناتكم واستخدامها وحمايتها عند استخدام تطبيقنا
            المتاح عبر الويب وتطبيق أندرويد (معرّف الحزمة: ai.sanad.app).
          </p>
        </div>

        {/* Sections */}
        <div className="space-y-8">

          {/* 1. Data Collection */}
          <Section number="١" title="البيانات التي نجمعها">
            <p className="mb-3">نجمع الأنواع التالية من البيانات عند استخدامكم لتطبيق سند:</p>
            <ul className="list-disc list-inside space-y-2 text-gray-400">
              <li>
                <strong className="text-gray-200">بيانات الحساب:</strong> البريد الإلكتروني وكلمة المرور (مشفّرة) عند إنشاء حساب جديد أو تسجيل الدخول.
              </li>
              <li>
                <strong className="text-gray-200">محادثات الاستشارة:</strong> الأسئلة القانونية التي تطرحونها والإجابات التي يقدّمها الذكاء الاصطناعي، وذلك لحفظ سجل المحادثات.
              </li>
              <li>
                <strong className="text-gray-200">بيانات الاستخدام:</strong> معلومات تقنية أساسية مثل نوع المتصفح ونظام التشغيل لتحسين أداء التطبيق.
              </li>
            </ul>
          </Section>

          {/* 2. How Data is Used */}
          <Section number="٢" title="كيف نستخدم بياناتكم">
            <p className="mb-3">نستخدم البيانات المجمّعة للأغراض التالية:</p>
            <ul className="list-disc list-inside space-y-2 text-gray-400">
              <li>تقديم خدمة الاستشارة القانونية بالذكاء الاصطناعي المتخصصة في أنظمة الأحوال الشخصية والإثبات والمرافعات الشرعية.</li>
              <li>حفظ سجل محادثاتكم السابقة حتى تتمكنوا من الرجوع إليها لاحقا.</li>
              <li>تحسين جودة الإجابات وأداء التطبيق بشكل عام.</li>
              <li>إدارة حساباتكم والتحقق من هويتكم.</li>
            </ul>
          </Section>

          {/* 3. Data Storage */}
          <Section number="٣" title="تخزين البيانات">
            <p className="mb-3">نقوم بتخزين بياناتكم بالطريقة التالية:</p>
            <ul className="list-disc list-inside space-y-2 text-gray-400">
              <li>
                تُخزّن جميع بيانات الحسابات والمحادثات في خوادم <strong className="text-gray-200">Supabase</strong> السحابية المؤمّنة.
              </li>
              <li>
                كلمات المرور مشفّرة ولا يمكن لأي شخص (بما في ذلك فريق التطوير) الاطلاع عليها بشكلها الأصلي.
              </li>
              <li>
                يتم الاحتفاظ ببيانات المحادثات طالما أن حسابكم نشط، ويمكنكم طلب حذفها في أي وقت.
              </li>
            </ul>
          </Section>

          {/* 4. Third-Party Services */}
          <Section number="٤" title="الخدمات الخارجية">
            <p className="mb-3">يعتمد تطبيق سند على الخدمات الخارجية التالية:</p>
            <div className="space-y-4">
              <ThirdPartyCard
                name="Google Gemini API"
                description="نستخدم واجهة برمجة تطبيقات Google Gemini لمعالجة أسئلتكم القانونية وتوليد الإجابات. يتم إرسال نص السؤال فقط إلى الخدمة ولا تتم مشاركة بيانات حسابكم الشخصية."
                link="https://ai.google.dev/terms"
              />
              <ThirdPartyCard
                name="Supabase"
                description="نستخدم Supabase لإدارة حسابات المستخدمين والمصادقة وتخزين بيانات المحادثات بشكل آمن في قواعد بيانات سحابية محمية."
                link="https://supabase.com/privacy"
              />
              <ThirdPartyCard
                name="Vercel"
                description="يتم استضافة التطبيق على منصة Vercel لتوفير أداء سريع وموثوق."
                link="https://vercel.com/legal/privacy-policy"
              />
            </div>
          </Section>

          {/* 5. Data Security */}
          <Section number="٥" title="أمان البيانات">
            <p className="mb-3">نتّخذ إجراءات أمنية لحماية بياناتكم تشمل:</p>
            <ul className="list-disc list-inside space-y-2 text-gray-400">
              <li>تشفير جميع الاتصالات باستخدام بروتوكول HTTPS/TLS.</li>
              <li>تشفير كلمات المرور باستخدام خوارزميات تشفير قوية (bcrypt).</li>
              <li>استخدام سياسات أمان صارمة على مستوى قاعدة البيانات (Row Level Security).</li>
              <li>عدم مشاركة بياناتكم الشخصية مع أي طرف ثالث لأغراض تسويقية أو إعلانية.</li>
            </ul>
            <p className="mt-3 text-gray-500 text-xs">
              على الرغم من اتخاذنا لكافة الإجراءات الأمنية المعقولة، لا يمكن ضمان أمان المعلومات المنقولة عبر الإنترنت بنسبة ١٠٠٪.
            </p>
          </Section>

          {/* 6. User Rights */}
          <Section number="٦" title="حقوق المستخدم">
            <p className="mb-3">يحق لكم كمستخدمين:</p>
            <ul className="list-disc list-inside space-y-2 text-gray-400">
              <li>
                <strong className="text-gray-200">حذف الحساب:</strong> يمكنكم طلب حذف حسابكم وجميع البيانات المرتبطة به بشكل نهائي عبر التواصل معنا.
              </li>
              <li>
                <strong className="text-gray-200">حذف المحادثات:</strong> يمكنكم حذف أي محادثة من سجل المحادثات مباشرة من داخل التطبيق.
              </li>
              <li>
                <strong className="text-gray-200">تصدير البيانات:</strong> يمكنكم طلب نسخة من بياناتكم المخزّنة لدينا عبر التواصل معنا.
              </li>
              <li>
                <strong className="text-gray-200">الوصول والتعديل:</strong> يمكنكم الوصول إلى بيانات حسابكم وتعديلها في أي وقت.
              </li>
            </ul>
          </Section>

          {/* 7. Cookies and Local Storage */}
          <Section number="٧" title="ملفات تعريف الارتباط والتخزين المحلي">
            <p className="mb-3">يستخدم التطبيق التقنيات التالية:</p>
            <ul className="list-disc list-inside space-y-2 text-gray-400">
              <li>
                <strong className="text-gray-200">ملفات تعريف الارتباط (Cookies):</strong> تُستخدم لإدارة جلسة تسجيل الدخول والحفاظ على حالة المصادقة.
              </li>
              <li>
                <strong className="text-gray-200">التخزين المحلي (Local Storage):</strong> يُستخدم لتخزين تفضيلات المستخدم وبيانات التطبيق التقدمي (PWA) لتمكين العمل دون اتصال بالإنترنت.
              </li>
              <li>
                <strong className="text-gray-200">Service Worker:</strong> يُستخدم لتوفير إمكانيات التطبيق التقدمي مثل التخزين المؤقت والإشعارات.
              </li>
            </ul>
          </Section>

          {/* 8. Contact Information */}
          <Section number="٨" title="معلومات التواصل">
            <p className="mb-4">
              إذا كان لديكم أي استفسارات أو مخاوف بشأن سياسة الخصوصية هذه أو ممارسات التعامل مع البيانات،
              يمكنكم التواصل معنا عبر:
            </p>
            <div className="bg-white/[0.03] rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5 text-primary-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
                </svg>
                <a href="mailto:support@sanad.ai" className="text-primary-400 hover:text-primary-300 transition-colors text-sm" dir="ltr">
                  support@sanad.ai
                </a>
              </div>
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5 text-primary-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
                </svg>
                <a href="https://legal-assistant-rosy.vercel.app" className="text-primary-400 hover:text-primary-300 transition-colors text-sm" dir="ltr">
                  legal-assistant-rosy.vercel.app
                </a>
              </div>
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5 text-primary-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                </svg>
                <span className="text-gray-300 text-sm">المملكة العربية السعودية</span>
              </div>
            </div>
          </Section>

          {/* 9. Changes to Policy */}
          <Section number="٩" title="التعديلات على سياسة الخصوصية">
            <p>
              نحتفظ بالحق في تعديل سياسة الخصوصية هذه في أي وقت. سيتم نشر أي تغييرات على هذه الصفحة
              مع تحديث تاريخ &quot;آخر تحديث&quot; في أعلى الصفحة. ننصحكم بمراجعة هذه السياسة بشكل دوري
              للاطلاع على أي تحديثات. استمراركم في استخدام التطبيق بعد نشر التعديلات يُعدّ قبولا منكم بالسياسة المحدّثة.
            </p>
          </Section>

          {/* Disclaimer */}
          <div className="bg-primary-500/5 border border-primary-500/10 rounded-2xl p-6 mt-12">
            <h3 className="text-sm font-bold text-primary-300 mb-2 font-heading">تنبيه مهم</h3>
            <p className="text-gray-400 text-xs leading-relaxed">
              تطبيق سند يقدّم معلومات قانونية عامة بالاستعانة بالذكاء الاصطناعي ولا يُعدّ بديلا عن الاستشارة القانونية المتخصصة
              من محامٍ مرخّص. الإجابات المقدّمة هي للاسترشاد فقط ولا تُشكّل رأيا قانونيا ملزما.
            </p>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-16 pt-8 border-t border-white/5 text-center">
          <p className="text-gray-500 text-xs">
            &copy; {new Date().getFullYear()} Sanad AI (سند) — جميع الحقوق محفوظة
          </p>
        </footer>
      </main>
    </div>
  );
}

/* ---- Helper Components ---- */

function Section({ number, title, children }: { number: string; title: string; children: React.ReactNode }) {
  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-primary-500/10 text-primary-400 text-sm font-bold shrink-0">
          {number}
        </span>
        <h2 className="text-xl font-bold text-white font-heading">{title}</h2>
      </div>
      <div className="text-gray-300 text-sm leading-relaxed pr-11">
        {children}
      </div>
    </section>
  );
}

function ThirdPartyCard({ name, description, link }: { name: string; description: string; link: string }) {
  return (
    <div className="bg-white/[0.03] rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-bold text-gray-200">{name}</h4>
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-primary-400 hover:text-primary-300 transition-colors"
          dir="ltr"
        >
          سياسة الخصوصية
          <svg className="w-3 h-3 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
          </svg>
        </a>
      </div>
      <p className="text-xs text-gray-400 leading-relaxed">{description}</p>
    </div>
  );
}
