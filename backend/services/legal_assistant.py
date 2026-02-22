"""
Claude API integration for legal consultations.
Includes retry logic for rate limits.
"""
from __future__ import annotations
import json
import time
from typing import Optional
import anthropic
from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL


def _call_claude_with_retry(client, max_retries=3, **kwargs):
    """Call Claude API with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt * 5  # 5s, 10s, 20s
                print(f"⏳ Rate limit hit, waiting {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries - 1:
                wait = 2 ** attempt * 5
                print(f"⏳ API overloaded, waiting {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise

SYSTEM_PROMPT = """أنت محامي سعودي متخصص في نظام الأحوال الشخصية، خبرة 20+ سنة. اسمك: المستشار القانوني الذكي.

## قواعد إلزامية
1. أجب حصرياً من المواد النظامية المرفقة في الرسالة — لا تستخدم معرفتك العامة أبداً
2. كل حكم تذكره يجب أن يكون مسنوداً بـ: رقم المادة + اسم النظام + نص المادة
3. لا تذكر أي رقم مادة غير موجود في النصوص المرفقة — لا تخترع مواداً
4. إذا لم تجد إجابة في المواد المرفقة قل: "لم أجد نصاً في المواد المتوفرة لديّ يعالج هذه المسألة"
5. نبّه عن المهل النظامية (اعتراض، عدة، رفع دعوى) وأن فواتها قد يُسقط الحق
6. استخدم المصطلحات القانونية الدقيقة واشرح الصعب منها

## هيكل الإجابة
1. **ملخص الموقف القانوني** (3 أسطر كحد أقصى)
2. **الأساس النظامي** (المواد المنطبقة مع نصوصها)
3. **التحليل القانوني** (تطبيق المواد على الحالة)
4. **الإجراءات المطلوبة** (الخطوات العملية والمحكمة المختصة)
5. **المهل النظامية** (إن وُجدت)
6. **تنبيهات مهمة**

اختم دائماً بـ: ⚖️ هذه استشارة أولية لا تُغني عن مراجعة محامي مرخص."""


def get_client() -> anthropic.Anthropic:
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY غير مُعَد. أضف المفتاح في ملف .env")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_legal_response(
    question: str,
    context: str,
    classification: dict,
    chat_history: Optional[list] = None,
) -> str:
    """Generate a legal response using Claude API."""
    client = get_client()
    messages = []

    if chat_history:
        messages.extend(chat_history)

    user_message = f"""السؤال: {question}
التصنيف: {classification.get('category', 'عام')} | {classification.get('intent', 'استشارة')}

📚 المواد النظامية المسترجعة:
{context}

⛔ أجب حصرياً من المواد أعلاه. لا تذكر مواد غير مقدمة لك."""

    messages.append({"role": "user", "content": user_message})

    response = _call_claude_with_retry(
        client,
        model=CLAUDE_MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    return response.content[0].text


def generate_draft(
    draft_type: str,
    case_details: dict,
    context: str,
) -> str:
    """Generate a legal document draft."""
    client = get_client()

    draft_prompts = {
        "lawsuit": "صياغة لائحة دعوى",
        "memo": "صياغة مذكرة قانونية",
        "appeal": "صياغة لائحة اعتراض",
        "response": "صياغة مذكرة جوابية",
        "khula": "صياغة طلب خلع",
        "custody": "صياغة طلب حضانة",
        "nafaqa": "صياغة طلب نفقة",
    }

    draft_name = draft_prompts.get(draft_type, "صياغة وثيقة قانونية")

    user_message = f"""المطلوب: {draft_name}

تفاصيل القضية:
{json.dumps(case_details, ensure_ascii=False, indent=2) if isinstance(case_details, dict) else str(case_details)}

---

المواد النظامية ذات الصلة:
{context}

---

قم بصياغة {draft_name} بناءً على:
1. تفاصيل القضية المقدمة
2. المواد النظامية ذات الصلة
3. الأعراف القانونية السعودية في صياغة المذكرات

يجب أن تتضمن الصياغة:
- مقدمة رسمية
- الوقائع
- الأسانيد النظامية (مع ذكر أرقام المواد)
- الطلبات
- الخاتمة"""

    response = _call_claude_with_retry(
        client,
        model=CLAUDE_MODEL,
        max_tokens=6000,
        system="أنت محامٍ سعودي متخصص في صياغة المذكرات القانونية. تعمل وفق نظام الأحوال الشخصية ونظام الإثبات السعوديين. اكتب بأسلوب قانوني رسمي واحترافي مع الإشارة لأرقام المواد ومصادرها.",
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
