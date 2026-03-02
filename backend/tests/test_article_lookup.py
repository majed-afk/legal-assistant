"""Tests for backend.rag.article_lookup — article pattern matching and lookup."""
import pytest
from unittest.mock import patch, MagicMock

from backend.rag.article_lookup import (
    _to_western_digits,
    _resolve_law_name,
    _ARTICLE_PATTERNS,
    _LAW_ALIASES,
    lookup_article,
)


# ===================================================================
# Arabic digit conversion
# ===================================================================

class TestArabicDigitConversion:
    """Tests for _to_western_digits function."""

    def test_arabic_to_western_single(self):
        assert _to_western_digits("٣٠") == "30"

    def test_arabic_to_western_all_digits(self):
        assert _to_western_digits("٠١٢٣٤٥٦٧٨٩") == "0123456789"

    def test_western_digits_unchanged(self):
        assert _to_western_digits("123") == "123"

    def test_mixed_digits(self):
        assert _to_western_digits("١2٣") == "123"

    def test_empty_string(self):
        assert _to_western_digits("") == ""

    def test_text_with_arabic_digits(self):
        assert _to_western_digits("المادة ١٥") == "المادة 15"


# ===================================================================
# Law name alias resolution
# ===================================================================

class TestLawNameResolution:
    """Tests for _resolve_law_name function."""

    def test_direct_alias_match(self):
        assert _resolve_law_name("الأحوال الشخصية") == "نظام الأحوال الشخصية"

    def test_alias_with_nizam_prefix(self):
        assert _resolve_law_name("نظام الأحوال الشخصية") == "نظام الأحوال الشخصية"

    def test_ithbat_alias(self):
        assert _resolve_law_name("الإثبات") == "نظام الإثبات"

    def test_murafaat_alias(self):
        assert _resolve_law_name("المرافعات") == "نظام المرافعات الشرعية"

    def test_muamalat_alias(self):
        assert _resolve_law_name("المعاملات المدنية") == "نظام المعاملات المدنية"

    def test_short_alias(self):
        assert _resolve_law_name("مدني") == "نظام المعاملات المدنية"

    def test_none_input(self):
        assert _resolve_law_name(None) is None

    def test_empty_string(self):
        assert _resolve_law_name("") is None

    def test_unknown_law_returns_none(self):
        assert _resolve_law_name("قانون غير معروف") is None

    def test_trailing_punctuation_stripped(self):
        assert _resolve_law_name("الإثبات؟") == "نظام الإثبات"

    def test_law_aliases_comprehensive(self):
        """All aliases in _LAW_ALIASES should resolve properly."""
        for alias, canonical in _LAW_ALIASES.items():
            result = _resolve_law_name(alias)
            assert result == canonical, f"Alias '{alias}' failed: expected '{canonical}', got '{result}'"


# ===================================================================
# Regex pattern matching
# ===================================================================

class TestArticlePatterns:
    """Tests for article reference regex pattern matching."""

    def test_pattern_ma_nass_al_mada(self):
        """'ما نص المادة 15 من نظام الأحوال الشخصية' should match."""
        text = "ما نص المادة 15 من نظام الأحوال الشخصية"
        matched = False
        for pattern in _ARTICLE_PATTERNS:
            m = pattern.search(text)
            if m:
                matched = True
                assert m.group(1) == "15"
                assert "الأحوال الشخصية" in (m.group(3) or "")
                break
        assert matched, "Pattern should match 'ما نص المادة 15 من نظام الأحوال الشخصية'"

    def test_pattern_atni_al_mada(self):
        """'عطني المادة 30 من نظام الإثبات' should match."""
        text = "عطني المادة 30 من نظام الإثبات"
        matched = False
        for pattern in _ARTICLE_PATTERNS:
            m = pattern.search(text)
            if m:
                matched = True
                assert m.group(1) == "30"
                assert "الإثبات" in (m.group(3) or "")
                break
        assert matched, "Pattern should match 'عطني المادة 30 من نظام الإثبات'"

    def test_pattern_arabic_digits(self):
        """Arabic digits like ٣٠ should be captured correctly."""
        text = "ما نص المادة ٣٠ من الإثبات"
        matched = False
        for pattern in _ARTICLE_PATTERNS:
            m = pattern.search(text)
            if m:
                matched = True
                assert m.group(1) == "٣٠"
                break
        assert matched, "Pattern should match Arabic digits"

    def test_pattern_with_question_mark(self):
        """Pattern should match with trailing Arabic question mark."""
        text = "ما نص المادة 10 من الأحوال الشخصية؟"
        matched = False
        for pattern in _ARTICLE_PATTERNS:
            m = pattern.search(text)
            if m:
                matched = True
                assert m.group(1) == "10"
                break
        assert matched, "Pattern should match with trailing ؟"

    def test_pattern_aatini_variant(self):
        """'أعطني المادة 5' should match."""
        text = "أعطني المادة 5"
        matched = False
        for pattern in _ARTICLE_PATTERNS:
            m = pattern.search(text)
            if m:
                matched = True
                assert m.group(1) == "5"
                break
        assert matched, "Pattern should match أعطني variant"

    def test_non_matching_query(self):
        """A regular question without article reference should not match."""
        text = "ما هي شروط الطلاق في السعودية؟"
        matched = False
        for pattern in _ARTICLE_PATTERNS:
            m = pattern.search(text)
            if m:
                matched = True
        assert not matched, "Non-article-reference query should not match"

    def test_sub_article_pattern(self):
        """Pattern should capture sub-article number like '100/2'."""
        text = "ما نص المادة 100/2 من نظام الأحوال الشخصية"
        matched = False
        for pattern in _ARTICLE_PATTERNS:
            m = pattern.search(text)
            if m:
                matched = True
                assert m.group(1) == "100"
                assert m.group(2) == "2"
                break
        assert matched, "Pattern should match sub-article notation"


# ===================================================================
# lookup_article (integration with mock data)
# ===================================================================

class TestLookupArticle:
    """Tests for the lookup_article function with mock article data."""

    @pytest.fixture(autouse=True)
    def setup_mock_articles(self):
        """Inject mock articles data for each test."""
        import backend.rag.article_lookup as module

        self._original_data = module._articles_data
        module._articles_data = [
            {
                "article_number": 15,
                "law": "نظام الأحوال الشخصية",
                "text": "نص المادة 15 للاختبار",
                "section": "الباب الأول",
                "chapter": "الفصل الأول",
                "topic": "زواج",
                "has_deadline": False,
                "deadline_details": None,
                "source_pages": "25",
            },
            {
                "article_number": 30,
                "law": "نظام الإثبات",
                "text": "نص المادة 30 من نظام الإثبات للاختبار",
                "section": "باب الشهادة",
                "chapter": "الفصل الثاني",
                "topic": "شهادة",
                "has_deadline": False,
                "deadline_details": None,
                "source_pages": "50",
            },
            {
                "article_number": 118,
                "law": "نظام الأحوال الشخصية",
                "text": "عدة المطلقة ثلاث حيضات",
                "section": "باب العدة",
                "chapter": "الفصل الخامس",
                "topic": "عدة",
                "has_deadline": True,
                "deadline_details": "ثلاث حيضات أو ثلاثة أشهر",
                "source_pages": "80",
            },
        ]
        yield
        module._articles_data = self._original_data

    def test_lookup_article_15_ahwal(self):
        """Looking up article 15 from personal status law should succeed."""
        result = lookup_article("ما نص المادة 15 من نظام الأحوال الشخصية")
        assert result is not None
        assert result["article_number"] == 15
        assert result["law"] == "نظام الأحوال الشخصية"
        assert "نص المادة 15 للاختبار" in result["response"]

    def test_lookup_article_30_ithbat(self):
        """Looking up article 30 from evidence law should succeed."""
        result = lookup_article("عطني المادة 30 من نظام الإثبات")
        assert result is not None
        assert result["article_number"] == 30
        assert result["law"] == "نظام الإثبات"

    def test_lookup_with_alias(self):
        """Law name alias should be resolved to canonical name."""
        result = lookup_article("ما نص المادة 15 من الأحوال الشخصية")
        assert result is not None
        assert result["law"] == "نظام الأحوال الشخصية"

    def test_lookup_article_with_deadline(self):
        """Article with deadline info should include deadline in response."""
        result = lookup_article("ما نص المادة 118 من الأحوال الشخصية")
        assert result is not None
        assert "مهلة" in result["response"]

    def test_lookup_nonexistent_article(self):
        """Looking up a non-existent article number should return None."""
        result = lookup_article("ما نص المادة 999 من نظام الأحوال الشخصية")
        assert result is None

    def test_lookup_non_article_query(self):
        """Non-article-reference queries should return None."""
        result = lookup_article("ما هي شروط الزواج؟")
        assert result is None

    def test_lookup_wrong_law_for_article(self):
        """Article number that exists in one law but queried for another should return None."""
        result = lookup_article("ما نص المادة 15 من نظام الإثبات")
        assert result is None

    def test_lookup_response_has_disclaimer(self):
        """Response should include the legal disclaimer."""
        result = lookup_article("ما نص المادة 15 من الأحوال الشخصية")
        assert result is not None
        assert "لا تُغني عن مراجعة محامي مرخص" in result["response"]

    def test_lookup_sources_populated(self):
        """Sources list should be populated with article metadata."""
        result = lookup_article("ما نص المادة 15 من الأحوال الشخصية")
        assert result is not None
        assert len(result["sources"]) > 0
        assert "section" in result["sources"][0]
        assert "topic" in result["sources"][0]

    def test_lookup_with_arabic_digits(self):
        """Arabic digits in the query should be converted and matched."""
        result = lookup_article("ما نص المادة ١٥ من الأحوال الشخصية")
        assert result is not None
        assert result["article_number"] == 15

    def test_lookup_empty_articles_returns_none(self):
        """When articles data is empty, lookup should return None."""
        import backend.rag.article_lookup as module
        module._articles_data = []
        result = lookup_article("ما نص المادة 15 من الأحوال الشخصية")
        assert result is None
