"""Tests for backend.services.deadline_calculator — legal deadline calculations."""
import pytest
from datetime import datetime, timedelta

from backend.services.deadline_calculator import calculate_deadline


# ===================================================================
# Input validation
# ===================================================================

class TestInputValidation:
    """Tests for input validation in calculate_deadline."""

    def test_invalid_date_format_returns_error(self):
        """Invalid date format should return an error message."""
        result = calculate_deadline("divorce", "2024/01/15")
        assert "error" in result
        assert "صيغة التاريخ" in result["error"]

    def test_invalid_date_string_returns_error(self):
        """Non-date string should return an error."""
        result = calculate_deadline("divorce", "not-a-date")
        assert "error" in result

    def test_unknown_event_type_returns_error(self):
        """Unknown event type should return an error."""
        result = calculate_deadline("unknown_event", "2024-06-01")
        assert "error" in result
        assert "غير معروف" in result["error"]

    def test_valid_date_format_accepted(self):
        """Valid YYYY-MM-DD date should be accepted without error."""
        result = calculate_deadline("divorce", "2024-06-01")
        assert "error" not in result


# ===================================================================
# Divorce deadlines
# ===================================================================

class TestDivorceDeadlines:
    """Tests for divorce-related deadline calculations."""

    def test_divorce_non_pregnant_iddah(self):
        """Non-pregnant divorce should calculate ~3 month iddah period."""
        result = calculate_deadline("divorce", "2024-06-01")
        assert len(result["deadlines"]) >= 1

        iddah = result["deadlines"][0]
        assert iddah["name"] == "عدة الطلاق"
        # ~90 days from June 1
        expected_end = (datetime(2024, 6, 1) + timedelta(days=90)).strftime("%Y-%m-%d")
        assert iddah["end_date"] == expected_end
        assert "المادة 118" in iddah["legal_basis"]

    def test_divorce_pregnant_iddah(self):
        """Pregnant divorce should indicate iddah ends at delivery."""
        result = calculate_deadline("divorce", "2024-06-01", {"is_pregnant": True})
        assert len(result["deadlines"]) >= 1

        iddah = result["deadlines"][0]
        assert iddah["name"] == "عدة الحامل"
        assert "بوضع الحمل" in iddah["end_date"]

    def test_revocable_divorce_includes_review_period(self):
        """Revocable divorce should include the review (مراجعة) period."""
        result = calculate_deadline("divorce", "2024-06-01", {"divorce_type": "revocable"})
        deadline_names = [d["name"] for d in result["deadlines"]]
        assert "مدة المراجعة" in deadline_names

    def test_irrevocable_divorce_no_review_period(self):
        """Irrevocable divorce should NOT include the review period."""
        result = calculate_deadline("divorce", "2024-06-01", {"divorce_type": "irrevocable"})
        deadline_names = [d["name"] for d in result["deadlines"]]
        assert "مدة المراجعة" not in deadline_names

    def test_divorce_has_documentation_note(self):
        """Divorce result should include the documentation note."""
        result = calculate_deadline("divorce", "2024-06-01")
        assert any("توثيق" in note for note in result["notes"])

    def test_divorce_response_structure(self):
        """Divorce response should have the expected structure."""
        result = calculate_deadline("divorce", "2024-06-01")
        assert result["event_type"] == "divorce"
        assert result["event_date"] == "2024-06-01"
        assert "deadlines" in result
        assert "notes" in result
        assert isinstance(result["deadlines"], list)
        assert isinstance(result["notes"], list)


# ===================================================================
# Death deadlines (widow's waiting period)
# ===================================================================

class TestDeathDeadlines:
    """Tests for death-related deadline calculations."""

    def test_death_non_pregnant_iddah(self):
        """Non-pregnant widow's iddah should be 4 months and 10 days (130 days)."""
        result = calculate_deadline("death", "2024-01-01")
        assert len(result["deadlines"]) >= 1

        iddah = result["deadlines"][0]
        assert "المتوفى عنها" in iddah["name"]
        expected_end = (datetime(2024, 1, 1) + timedelta(days=130)).strftime("%Y-%m-%d")
        assert iddah["end_date"] == expected_end

    def test_death_pregnant_iddah(self):
        """Pregnant widow's iddah should end at delivery."""
        result = calculate_deadline("death", "2024-01-01", {"is_pregnant": True})
        iddah = result["deadlines"][0]
        assert "حامل" in iddah["name"]
        assert "بوضع الحمل" in iddah["end_date"]

    def test_death_has_inheritance_note(self):
        """Death result should include note about inheritance procedure."""
        result = calculate_deadline("death", "2024-01-01")
        assert any("حصر الورثة" in note for note in result["notes"])

    def test_death_iddah_starts_from_date(self):
        """Iddah note should mention it starts from date of death."""
        result = calculate_deadline("death", "2024-01-01")
        assert any("تاريخ الوفاة" in note for note in result["notes"])


# ===================================================================
# Judgment deadlines
# ===================================================================

class TestJudgmentDeadlines:
    """Tests for judgment-related deadline calculations."""

    def test_judgment_appeal_period(self):
        """Judgment should have a 30-day appeal period."""
        result = calculate_deadline("judgment", "2024-06-01")
        assert len(result["deadlines"]) >= 1

        appeal = result["deadlines"][0]
        assert "اعتراض" in appeal["name"]
        expected_end = (datetime(2024, 6, 1) + timedelta(days=30)).strftime("%Y-%m-%d")
        assert appeal["end_date"] == expected_end

    def test_judgment_note_about_start_date(self):
        """Judgment result should note that period starts from receiving the judgment copy."""
        result = calculate_deadline("judgment", "2024-06-01")
        assert any("تسلم صورة الحكم" in note for note in result["notes"])


# ===================================================================
# Custody deadlines
# ===================================================================

class TestCustodyDeadlines:
    """Tests for custody-related deadline calculations."""

    def test_custody_child_under_2(self):
        """Child under 2 should have mother's custody deadline."""
        result = calculate_deadline("custody", "2024-06-01", {"child_age": 1})
        deadline_names = [d["name"] for d in result["deadlines"]]
        assert any("أقل من سنتين" in name for name in deadline_names)

    def test_custody_child_over_2(self):
        """Child over 2 should NOT have the under-2 custody deadline."""
        result = calculate_deadline("custody", "2024-06-01", {"child_age": 5})
        deadline_names = [d["name"] for d in result["deadlines"]]
        assert not any("أقل من سنتين" in name for name in deadline_names)

    def test_custody_choice_age(self):
        """All custody results should mention choice age at 15."""
        result = calculate_deadline("custody", "2024-06-01", {"child_age": 5})
        deadline_names = [d["name"] for d in result["deadlines"]]
        assert any("تخيير" in name for name in deadline_names)


# ===================================================================
# Appeal deadlines
# ===================================================================

class TestAppealDeadlines:
    """Tests for appeal-related deadline calculations."""

    def test_appeal_period_30_days(self):
        """Appeal deadline should be 30 days from event date."""
        result = calculate_deadline("appeal", "2024-06-01")
        assert len(result["deadlines"]) >= 1

        appeal = result["deadlines"][0]
        assert "استئناف" in appeal["name"]
        expected_end = (datetime(2024, 6, 1) + timedelta(days=30)).strftime("%Y-%m-%d")
        assert appeal["end_date"] == expected_end

    def test_appeal_includes_supreme_court(self):
        """Appeal result should include supreme court (نقض) deadline."""
        result = calculate_deadline("appeal", "2024-06-01")
        deadline_names = [d["name"] for d in result["deadlines"]]
        assert any("نقض" in name for name in deadline_names)

    def test_appeal_response_structure(self):
        """Appeal response should have the standard structure."""
        result = calculate_deadline("appeal", "2024-06-01")
        assert result["event_type"] == "appeal"
        assert result["event_date"] == "2024-06-01"
        assert isinstance(result["deadlines"], list)
        assert len(result["deadlines"]) >= 2  # appeal + supreme court


# ===================================================================
# Edge cases
# ===================================================================

class TestEdgeCases:
    """Tests for edge cases in deadline calculations."""

    def test_no_details_defaults_gracefully(self):
        """Passing None for details should not crash."""
        result = calculate_deadline("divorce", "2024-06-01", None)
        assert "error" not in result
        assert len(result["deadlines"]) >= 1

    def test_empty_details_defaults_gracefully(self):
        """Passing empty dict for details should not crash."""
        result = calculate_deadline("divorce", "2024-06-01", {})
        assert "error" not in result

    def test_leap_year_date(self):
        """Leap year dates should be handled correctly."""
        result = calculate_deadline("divorce", "2024-02-29")
        assert "error" not in result
        assert len(result["deadlines"]) >= 1

    def test_end_of_year_date(self):
        """End of year dates should calculate correctly across year boundary."""
        result = calculate_deadline("judgment", "2024-12-15")
        assert "error" not in result
        appeal = result["deadlines"][0]
        # 30 days from Dec 15 = Jan 14 next year
        expected = (datetime(2024, 12, 15) + timedelta(days=30)).strftime("%Y-%m-%d")
        assert appeal["end_date"] == expected

    def test_all_event_types_have_deadlines(self):
        """All valid event types should produce at least one deadline."""
        for event_type in ["divorce", "death", "judgment", "custody", "appeal"]:
            result = calculate_deadline(event_type, "2024-06-01")
            assert "error" not in result, f"Event type '{event_type}' produced an error"
            assert len(result["deadlines"]) >= 1, f"Event type '{event_type}' has no deadlines"
