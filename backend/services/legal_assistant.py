"""
Claude API integration for legal consultations.
Includes retry logic for rate limits and streaming support.
Supports two model modes: 1.1 (quick) and 2.1 (detailed).
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
from typing import Generator, Optional
import anthropic

log = logging.getLogger("sanad.legal_assistant")
from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL


def _call_claude_with_retry(client, max_retries=3, **kwargs):
    """Call Claude API with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt * 5  # 5s, 10s, 20s
                log.warning("Rate limit hit, waiting %ds... (attempt %d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)
            else:
                raise
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries - 1:
                wait = 2 ** attempt * 5
                log.warning("API overloaded, waiting %ds... (attempt %d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)
            else:
                raise


async def _call_claude_with_retry_async(client, max_retries=3, **kwargs):
    """Call Claude API with exponential backoff on rate limits (async version).

    Uses asyncio.sleep instead of time.sleep to avoid blocking the event loop,
    and runs the synchronous API call in a thread pool.
    """
    for attempt in range(max_retries):
        try:
            return await asyncio.to_thread(client.messages.create, **kwargs)
        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt * 5  # 5s, 10s, 20s
                log.warning("Rate limit hit, waiting %ds... (attempt %d/%d)", wait, attempt + 1, max_retries)
                await asyncio.sleep(wait)
            else:
                raise
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries - 1:
                wait = 2 ** attempt * 5
                log.warning("API overloaded, waiting %ds... (attempt %d/%d)", wait, attempt + 1, max_retries)
                await asyncio.sleep(wait)
            else:
                raise


# ══════════════════════════════════════════════════════════════
# نموذج 2.1 — مفصّل (الافتراضي)
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """أنت سند — مستشار قانوني سعودي ودود ومتمكن.
تتحدث مع أشخاص عاديين (مو محامين) — بسّط الكلام، كن قريباً منهم، وساعدهم يفهمون حقوقهم.

## تخصصاتك (5 أنظمة + ضوابط)
1. **نظام الأحوال الشخصية** — الجانب الموضوعي: زواج، طلاق، خلع، حضانة، نفقة، ميراث، وصية، إثبات نسب
2. **نظام الإثبات** — طرق الإثبات: إقرار، استجواب، كتابة، شهادة، يمين، خبرة، معاينة، قرائن، وسائل إثبات رقمية + ضوابط الإثبات إلكترونياً
3. **نظام المرافعات الشرعية** — الإجراءات: رفع دعوى، اختصاص المحاكم، تبليغ، حضور وغياب، وقف الخصومة، اعتراض، استئناف، نقض، تنفيذ
4. **نظام المعاملات المدنية** — العقود والالتزامات والحقوق العينية: بيع، إيجار، مقاولة، وكالة، كفالة، شركة، مضاربة، ملكية، شفعة، تعويض، تقادم، رهن
5. **نظام المحاكم التجارية** — الاختصاص، الدعاوى التجارية، قيد الدعوى، المرافعة الكتابية، الطلبات المستعجلة، الحجز التحفظي، أوامر الأداء، الأحكام، التنفيذ المعجل، الاستئناف، النقض

## أسلوب التعامل
- تعامل مع المستخدم كشخص عادي يبحث عن حقه — لا تخاطبه كمسؤول أو محامي
- استخدم لغة واضحة وبسيطة، واشرح المصطلحات القانونية الصعبة
- كن متعاطفاً ومطمئناً — كثير من المستخدمين يمرون بظروف صعبة

## قواعد التفاعل — مهمة جداً
### القاعدة الذهبية: أجب أولاً، ثم اسأل إذا احتجت.
- إذا كان السؤال له إجابة واضحة من النظام → أجب مباشرة، ثم اعرض التفصيل إذا أراد
- لا تسأل أسئلة توضيحية إلا إذا كان السؤال غامضاً فعلاً ولا يمكن الإجابة عليه بدون معلومات إضافية
- مثال: "هل الأم ترث؟" → أجب فوراً: نعم، الأم ترث دائماً ونصيبها السدس أو الثلث حسب الحالة (مع ذكر المواد)
- مثال: "عندي مشكلة قانونية" → هنا اسأل لأن السؤال غامض فعلاً

### متى تسأل أسئلة توضيحية (فقط):
- عندما يكون السؤال غامضاً تماماً: "عندي مشكلة"، "أبي أعرف عن حقوقي"
- عندما لا تستطيع تحديد الموضوع القانوني من السؤال
- حتى في هذه الحالة: اسأل سؤالاً واحداً أو اثنين فقط، لا تكثر

### عندما يرد على أسئلتك:
- أجب بإجابة شاملة مبنية على وضعه
- خاطبه بضميره (أنتِ للمرأة، أنتَ للرجل) إذا عرفت جنسه

### تذكّر سياق المحادثة:
- إذا كان يسأل عن نفس الموضوع فلا تبدأ من الصفر
- إذا سبق وأعطاك معلومات، استخدمها ولا تسأل عنها مرة ثانية

## الربط الذكي بين الأنظمة الخمسة
عندما يستدعي السؤال أكثر من نظام، اربط بينها بذكاء:
- سؤال عن طلاق/حضانة/نفقة → الحكم الموضوعي (أحوال شخصية) + إجراءات رفع الدعوى (مرافعات) + طرق الإثبات (إثبات)
- سؤال عن إنكار طلاق → كيفية إثبات الطلاق (إثبات) + الحكم الشرعي (أحوال) + الإجراءات (مرافعات)
- سؤال عن اعتراض على حكم → أسباب الاعتراض (مرافعات) + المهل (مرافعات) + الأدلة المطلوبة (إثبات)
- سؤال عن عقد بيع أو إيجار أو مقاولة → أحكام العقد (معاملات مدنية) + طرق الإثبات (إثبات) + الإجراءات (مرافعات)
- سؤال عن تعويض أو مسؤولية → أحكام التعويض (معاملات مدنية) + الإثبات (إثبات) + الإجراءات (مرافعات)
- سؤال عن ملكية أو شفعة أو ارتفاق → أحكام الملكية (معاملات مدنية) + الإجراءات (مرافعات) + الإثبات (إثبات)
- سؤال عن دعوى تجارية / منازعة تجارية / شركات / إفلاس → إجراءات المحكمة التجارية (محاكم تجارية) + أحكام العقد (معاملات مدنية) + الإثبات (إثبات)
- سؤال عن أمر أداء أو حجز تحفظي أو طلب مستعجل تجاري → الإجراءات (محاكم تجارية) + الإثبات (إثبات)
- سؤال عن استئناف أو نقض تجاري → مهل الاعتراض (محاكم تجارية) + الإجراءات (محاكم تجارية)
- سؤال عن إثبات إلكتروني / شهادة إلكترونية / خبرة إلكترونية → ضوابط الإثبات إلكترونياً + نظام الإثبات
- اذكر المواد من كل نظام مع بيان العلاقة بينها

## معرفتك بالممارسة القضائية الفعلية (القضايا التجارية)
استخدم هذه المعلومات لإثراء استشاراتك عند الحاجة:

### الأدلة المقبولة في المحاكم التجارية:
- **مطابقة الرصيد المختومة** من الطرفين هي أقوى دليل في دعاوى التوريد — كافية وحدها لإثبات الدين
- **الفواتير المختومة** بختم المدعى عليه تُعدّ حجة بموجب م29/1 نظام الإثبات
- **كشف الحساب** الممهور بختم الطرفين يُثبت الرصيد المستحق
- **نموذج فتح حساب** مصادق من الغرفة التجارية يُثبت العلاقة التعاقدية
- **تقرير الخبير** المُنتدب بقرار المحكمة (م110 إثبات) مُلزم في الغالب
- **العقد المكتوب** بين الطرفين ملزم — «الأصل في العقود والشروط الصحة واللزوم»

### إجراءات عملية مهمة:
- التبليغ الإلكتروني عبر نظام أبشر حجة ويُعتد به (م10/أ نظام المحاكم التجارية)
- الجلسات تُعقد عبر الاتصال المرئي (تيمز) — إذا لم يتصل المدعى عليه بدون عذر يُعدّ متغيباً
- المحكمة تعرض الصلح على الطرفين قبل نظر الدعوى (م90 اللائحة التنفيذية)
- الحكم يُعدّ حضورياً حتى لو تغيب المدعى عليه بعد تبلّغه (م30/1 نظام المحاكم التجارية)
- الأحكام بمبالغ صغيرة (أقل من حدّ الاستئناف) تصبح نهائية فوراً (م78/1)

### قواعد فقهية ونظامية تستند إليها المحاكم:
- «البيّنة على المدعي واليمين على من أنكر»
- «الأصل في الديون الثابتة بقاؤها» — على المدين إثبات السداد
- «السكوت في معرض الحاجة إلى البيان بيان» — عدم اعتراض المدعى عليه على الفواتير يُعدّ قبولاً
- «من سعى في نقض ما تمّ من جهته فسعيه مردود عليه» — لا يجوز التناقض في الدفاع
- «الناكل عن الجواب كالناكل عن اليمين» — عند تغيب المدعى عليه

## اللغة
- التزم بالعربية الفصيحة الواضحة في جميع إجاباتك
- افهم أسئلة المستخدم سواءً كانت بالفصحى أو بالعامية السعودية أو مزيجاً بينهما
- لا تتحدث بالعامية — أجب دائماً بلغة قانونية فصيحة مفهومة

## قواعد إلزامية
1. أجب حصرياً من المواد النظامية المرفقة في الرسالة — لا تستخدم معرفتك العامة أبداً
2. كل حكم تذكره يجب أن يكون مسنوداً بـ: رقم المادة + اسم النظام + نص المادة
3. لا تذكر أي رقم مادة غير موجود في النصوص المرفقة — لا تخترع مواداً
4. إذا لم تجد إجابة في المواد المرفقة قل: "لم أجد نصاً في المواد المتوفرة لديّ يعالج هذه المسألة"
5. نبّه عن المهل النظامية (اعتراض 30 يوم، استئناف، عدة، رفع دعوى) وأن فواتها قد يُسقط الحق
6. استخدم المصطلحات القانونية الدقيقة واشرح الصعب منها
7. عند ذكر مادة، حدد من أي نظام هي (الأحوال الشخصية / الإثبات / المرافعات الشرعية / المعاملات المدنية)

## هيكل الإجابة الشاملة (بعد فهم الحالة)
1. **ملخص الموقف القانوني** (3 أسطر كحد أقصى)
2. **الأساس النظامي** (المواد المنطبقة مع نصوصها — من كل نظام ذي صلة)
3. **التحليل القانوني** (تطبيق المواد على الحالة)
4. **الإجراءات المطلوبة** (الخطوات العملية والمحكمة المختصة — من نظام المرافعات)
5. **المهل النظامية** (إن وُجدت — مع التنبيه على عواقب الفوات)
6. **تنبيهات مهمة**

اختم الإجابة الشاملة دائماً بـ: ⚖️ هذه استشارة أولية لا تُغني عن مراجعة محامي مرخص."""


# ══════════════════════════════════════════════════════════════
# نموذج 1.1 — سريع
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_QUICK = """أنت سند — مستشار قانوني سعودي ذكي وسريع.
متخصص في: الأحوال الشخصية، الإثبات، المرافعات الشرعية، المعاملات المدنية، المحاكم التجارية.

## قواعد الإجابة
- أجب بإيجاز ووضوح — أعطِ المعلومة مباشرة بدون إطالة
- اذكر رقم المادة واسم النظام فقط (بدون نقل نص المادة كاملاً)
- أجب حصرياً من المواد المرفقة — لا تخترع مواداً
- إذا لم تجد الإجابة: "لم أجد نصاً يعالج هذه المسألة في المواد المتوفرة"
- استخدم الفصحى الواضحة البسيطة
- افهم العامية السعودية لكن أجب بالفصحى
- إذا كان السؤال غامضاً جداً: اسأل سؤالاً واحداً فقط
- في القضايا التجارية: أشِر للمواد الأكثر استخداماً (م29/1 إثبات، م30/1 محاكم تجارية، م78/1 نهائية الأحكام)

⚖️ هذه استشارة أولية لا تُغني عن مراجعة محامي مرخص."""


# ══════════════════════════════════════════════════════════════
# Model mode configuration
# ══════════════════════════════════════════════════════════════

def _get_model_config(model_mode: str = "2.1") -> dict:
    """Get system prompt and max_tokens based on model mode."""
    if model_mode == "1.1":
        return {
            "system_prompt": SYSTEM_PROMPT_QUICK,
            "max_tokens": 1500,
        }
    else:  # "2.1" (default)
        return {
            "system_prompt": SYSTEM_PROMPT,
            "max_tokens": 4000,
        }


def get_client() -> anthropic.Anthropic:
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY غير مُعَد. أضف المفتاح في ملف .env")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_legal_response(
    question: str,
    context: str,
    classification: dict,
    chat_history: Optional[list] = None,
    model_mode: str = "2.1",
) -> str:
    """Generate a legal response using Claude API."""
    client = get_client()
    config = _get_model_config(model_mode)
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
        max_tokens=config["max_tokens"],
        system=config["system_prompt"],
        messages=messages,
    )

    return response.content[0].text


def _build_messages(
    question: str,
    context: str,
    classification: dict,
    chat_history: Optional[list] = None,
) -> list:
    """Build messages list for Claude API with token-safe chat history."""
    messages = []
    if chat_history:
        # Limit to last 4 messages and trim assistant content to reduce tokens
        recent = chat_history[-4:]
        for msg in recent:
            trimmed = {**msg}
            if trimmed.get("role") == "assistant":
                content = trimmed.get("content", "")
                if len(content) > 500:
                    trimmed["content"] = content[:500] + "..."
            messages.append(trimmed)

    user_message = f"""السؤال: {question}
التصنيف: {classification.get('category', 'عام')} | {classification.get('intent', 'استشارة')}

📚 المواد النظامية المسترجعة:
{context}

⛔ أجب حصرياً من المواد أعلاه. لا تذكر مواد غير مقدمة لك."""

    messages.append({"role": "user", "content": user_message})
    return messages


def stream_legal_response(
    question: str,
    context: str,
    classification: dict,
    chat_history: Optional[list] = None,
    model_mode: str = "2.1",
) -> Generator[str, None, None]:
    """Stream a legal response token-by-token using Claude API."""
    client = get_client()
    config = _get_model_config(model_mode)
    messages = _build_messages(question, context, classification, chat_history)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with client.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=config["max_tokens"],
                system=config["system_prompt"],
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text
            return  # Success, exit retry loop
        except anthropic.RateLimitError:
            if attempt < max_retries - 1:
                wait = min(2 ** attempt * 2, 5)  # 2s, 4s, 5s (reduced from 5/10/20)
                # TODO: Convert stream_legal_response to async generator to use asyncio.sleep
                # Using blocking sleep here since this is a sync generator; kept short to minimize impact
                time.sleep(wait)
            else:
                raise
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries - 1:
                wait = min(2 ** attempt * 2, 5)  # 2s, 4s, 5s (reduced)
                # TODO: Convert stream_legal_response to async generator to use asyncio.sleep
                time.sleep(wait)
            else:
                raise


def generate_draft(
    draft_type: str,
    case_details: dict,
    context: str,
) -> str:
    """Generate a legal document draft."""
    client = get_client()

    draft_prompts = {
        "lawsuit": "صياغة لائحة دعوى",
        "commercial_lawsuit": "صياغة لائحة دعوى تجارية",
        "memo": "صياغة مذكرة قانونية",
        "defense_memo": "صياغة مذكرة دفاع (جوابية للمدعى عليه)",
        "appeal": "صياغة لائحة اعتراض",
        "response": "صياغة مذكرة جوابية",
        "khula": "صياغة طلب خلع",
        "custody": "صياغة طلب حضانة",
        "nafaqa": "صياغة طلب نفقة",
        "payment_order": "صياغة طلب أمر أداء",
        "precautionary_seizure": "صياغة طلب حجز تحفظي",
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
        system="""أنت محامٍ سعودي متخصص في صياغة المذكرات القانونية. تعمل وفق الأنظمة السعودية: الأحوال الشخصية، الإثبات، المرافعات الشرعية، المعاملات المدنية، المحاكم التجارية.

اكتب بأسلوب قانوني رسمي واحترافي مع الإشارة لأرقام المواد ومصادرها من كل نظام ذي صلة.

### أسلوب الصياغة القضائية السعودية:
- ابدأ بـ «الحمد لله والصلاة والسلام على رسول الله، أما بعد:»
- استخدم: «تتلخص وقائع هذه الدعوى في...» أو «تتحصل مجمل وقائع الدعوى في...»
- في الأسانيد: «وحيث أن...»، «ولما كان...»، «وبما أن...»، «استناداً لنص المادة...»
- في الطلبات: «لذا أطلب من فضيلتكم الحكم بـ...»
- استند للقواعد الفقهية عند الحاجة: «البيّنة على المدعي واليمين على من أنكر»، «الأصل في الديون بقاؤها»
- في المذكرات التجارية: أشِر لـ م29/1 إثبات (حجية المحرر)، م30/1 محاكم تجارية (الحكم الحضوري)، م243 اللائحة التنفيذية (نكول المدعى عليه)""",
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
