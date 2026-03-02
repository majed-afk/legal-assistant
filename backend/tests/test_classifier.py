"""Tests for backend.rag.classifier — query classification for legal questions."""
import pytest

from backend.rag.classifier import classify_query, CATEGORY_KEYWORDS, INTENT_PATTERNS


# ===================================================================
# Category detection
# ===================================================================

class TestCategoryDetection:
    """Tests for category detection in classify_query."""

    def test_talaq_keyword(self):
        """Query containing 'طلاق' should be classified under the divorce category."""
        result = classify_query("ما حكم الطلاق في حال غياب الزوج؟")
        assert result["category"] == "طلاق"

    def test_nafaqa_keyword(self):
        """Query about child support should be classified under nafaqa (نفقة)."""
        result = classify_query("كم نفقة الأطفال بعد الطلاق؟")
        # "نفقة" and "الأطفال" should match nafaqa category
        assert "نفقة" in result["category"] or "نفقة" in result["all_categories"]

    def test_hadana_keyword(self):
        """Query about custody should classify as حضانة."""
        result = classify_query("من له حق الحضانة بعد الطلاق؟")
        assert "حضانة" in result["all_categories"]

    def test_irth_keyword(self):
        """Query about inheritance should classify under إرث."""
        result = classify_query("كيف يتم توزيع الميراث على الورثة؟")
        assert "إرث" in result["all_categories"]

    def test_ithbat_keyword(self):
        """Query about evidence should classify under إثبات."""
        result = classify_query("ما هي شروط الإثبات في المحكمة؟")
        assert "إثبات" in result["all_categories"]

    def test_zawaj_keyword(self):
        """Query about marriage should classify under زواج."""
        result = classify_query("ما شروط عقد الزواج الشرعي؟")
        assert result["category"] == "زواج"

    def test_mahr_keyword(self):
        """Query about dowry should classify under مهر."""
        result = classify_query("كم مهر المثل في السعودية؟")
        assert "مهر" in result["all_categories"]

    def test_unknown_vague_query(self):
        """Vague or unrecognizable query should return 'عام' category."""
        result = classify_query("سؤال عشوائي بدون كلمات مفتاحية")
        assert result["category"] == "عام"
        assert "عام" in result["all_categories"]

    def test_multiple_categories_picks_highest_score(self):
        """When multiple categories match, the one with the most keywords wins."""
        # "طلاق" and "نفقة" both appear, but if more talaq keywords match it should pick talaq
        result = classify_query("طلاق بائن وطلقة رجعية ونفقة")
        # "طلاق" has more keyword matches (طلاق, بائن, طلقة, رجعي)
        assert result["category"] == "طلاق"

    def test_commercial_court_keyword(self):
        """Query about commercial courts should classify under محكمة_تجارية."""
        result = classify_query("كيف أرفع دعوى تجارية في المحكمة التجارية؟")
        assert "محكمة_تجارية" in result["all_categories"]

    def test_electronic_evidence_keyword(self):
        """Query about electronic evidence should classify under إثبات_إلكتروني."""
        result = classify_query("ما هي ضوابط إجراءات الإثبات إلكترونياً؟")
        assert "إثبات_إلكتروني" in result["all_categories"]

    def test_civil_transactions_keyword(self):
        """Query about contracts should classify under عقد."""
        result = classify_query("ما هي شروط بطلان العقد؟")
        assert "عقد" in result["all_categories"]


# ===================================================================
# Intent detection
# ===================================================================

class TestIntentDetection:
    """Tests for intent detection in classify_query."""

    def test_info_intent(self):
        """'ما نص المادة 15' should be detected as 'معلومة' intent."""
        result = classify_query("ما هي المادة 15 من نظام الأحوال الشخصية؟")
        assert result["intent"] == "معلومة"

    def test_drafting_intent(self):
        """Drafting-related queries should be detected as 'صياغة' intent."""
        result = classify_query("اكتب لي مذكرة دعوى طلاق")
        assert result["intent"] == "صياغة"

    def test_consultation_intent(self):
        """'هل يحق لي' type queries should be detected as 'استشارة' intent."""
        result = classify_query("هل يحق لي طلب الطلاق؟")
        assert result["intent"] == "استشارة"

    def test_analysis_intent(self):
        """Analysis-related queries should be detected as 'تحليل' intent."""
        result = classify_query("ما فرص نجاح الدعوى؟")
        assert result["intent"] == "تحليل"

    def test_deadline_intent(self):
        """Deadline-related queries should be detected as 'مهلة' intent."""
        result = classify_query("ما مهلة الاستئناف")
        assert result["intent"] == "مهلة"

    def test_default_intent_is_consultation(self):
        """When no specific intent is matched, default should be 'استشارة'."""
        result = classify_query("أبي أعرف عن حقوقي")
        # This does not match any specific pattern, so default is consultation
        assert result["intent"] == "استشارة"


# ===================================================================
# Urgency detection
# ===================================================================

class TestUrgencyDetection:
    """Tests for urgency detection in classify_query."""

    def test_urgent_keyword(self):
        """Query with 'عاجل' should be marked urgent."""
        result = classify_query("سؤال عاجل عن الطلاق")
        assert result["urgency"] == "عاجل"

    def test_immediate_keyword(self):
        """Query with 'فوري' should be marked urgent."""
        result = classify_query("أحتاج جواب فوري عن الحضانة")
        assert result["urgency"] == "عاجل"

    def test_emergency_keyword(self):
        """Query with 'طوارئ' should be marked urgent."""
        result = classify_query("حالة طوارئ تتعلق بالحضانة")
        assert result["urgency"] == "عاجل"

    def test_now_keyword(self):
        """Query with 'الآن' should be marked urgent."""
        result = classify_query("أحتاج مساعدة الآن في قضية طلاق")
        assert result["urgency"] == "عاجل"

    def test_normal_urgency(self):
        """Query without urgency keywords should be marked normal."""
        result = classify_query("ما هي شروط الطلاق؟")
        assert result["urgency"] == "عادي"


# ===================================================================
# Deadline flag
# ===================================================================

class TestDeadlineFlag:
    """Tests for deadline detection flag in classify_query."""

    def test_deadline_keywords_detected(self):
        """Queries with deadline-related keywords should flag needs_deadline_check."""
        result = classify_query("كم مهلة الاعتراض على الحكم؟")
        assert result["needs_deadline_check"] is True

    def test_duration_keyword_detected(self):
        """Queries with 'مدة' should flag needs_deadline_check."""
        result = classify_query("ما مدة العدة بعد الطلاق؟")
        assert result["needs_deadline_check"] is True

    def test_no_deadline_flag(self):
        """Queries without deadline keywords should not set the flag."""
        result = classify_query("ما شروط الزواج؟")
        assert result["needs_deadline_check"] is False


# ===================================================================
# Response structure
# ===================================================================

class TestClassifyQueryStructure:
    """Tests for the overall structure of classify_query responses."""

    def test_return_has_all_required_keys(self):
        """classify_query should return all expected keys."""
        result = classify_query("سؤال قانوني عام")
        assert "category" in result
        assert "intent" in result
        assert "urgency" in result
        assert "needs_deadline_check" in result
        assert "all_categories" in result

    def test_all_categories_is_list(self):
        """all_categories should always be a list."""
        result = classify_query("ما هو الطلاق؟")
        assert isinstance(result["all_categories"], list)
        assert len(result["all_categories"]) > 0

    def test_category_keywords_dict_populated(self):
        """CATEGORY_KEYWORDS should have entries for all major legal areas."""
        expected = ["طلاق", "نفقة", "حضانة", "إرث", "زواج", "مهر", "إثبات", "مرافعات"]
        for cat in expected:
            assert cat in CATEGORY_KEYWORDS, f"Missing category: {cat}"

    def test_intent_patterns_populated(self):
        """INTENT_PATTERNS should have all expected intent types."""
        expected = ["استشارة", "صياغة", "تحليل", "معلومة", "مهلة"]
        for intent in expected:
            assert intent in INTENT_PATTERNS, f"Missing intent: {intent}"
