"""
Legal deadline calculator for Saudi Personal Status Law.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional


def calculate_deadline(event_type: str, event_date: str, details: Optional[dict] = None) -> dict:
    """
    Calculate legal deadlines based on event type.

    Args:
        event_type: Type of event (divorce, death, judgment, appeal, etc.)
        event_date: Event date in YYYY-MM-DD format (Gregorian)
        details: Additional details (e.g., pregnancy status)
    """
    try:
        date = datetime.strptime(event_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "صيغة التاريخ غير صحيحة. استخدم YYYY-MM-DD"}

    details = details or {}
    result = {
        "event_type": event_type,
        "event_date": event_date,
        "deadlines": [],
        "notes": [],
    }

    if event_type == "divorce":
        result = _calculate_divorce_deadlines(date, details, result)
    elif event_type == "death":
        result = _calculate_death_deadlines(date, details, result)
    elif event_type == "judgment":
        result = _calculate_judgment_deadlines(date, details, result)
    elif event_type == "custody":
        result = _calculate_custody_deadlines(date, details, result)
    elif event_type == "appeal":
        result = _calculate_appeal_deadlines(date, details, result)
    else:
        result["error"] = f"نوع الحدث غير معروف: {event_type}"

    return result


def _calculate_divorce_deadlines(date: datetime, details: dict, result: dict) -> dict:
    """Calculate divorce-related deadlines."""
    is_pregnant = details.get("is_pregnant", False)
    divorce_type = details.get("divorce_type", "revocable")  # revocable or irrevocable

    if is_pregnant:
        result["deadlines"].append({
            "name": "عدة الحامل",
            "description": "تنتهي العدة بوضع الحمل (المادة 120)",
            "end_date": "بوضع الحمل",
            "legal_basis": "المادة 120 من نظام الأحوال الشخصية",
        })
        result["notes"].append("عدة الحامل تنتهي بوضع الحمل وليس بمدة محددة")
    else:
        # Three menstrual cycles or 3 months
        iddah_end = date + timedelta(days=90)  # ~3 months approximation
        result["deadlines"].append({
            "name": "عدة الطلاق",
            "description": "ثلاث حيضات، أو ثلاثة أشهر لمن لا تحيض (المادة 118)",
            "end_date": iddah_end.strftime("%Y-%m-%d"),
            "approximate": True,
            "legal_basis": "المادة 118 من نظام الأحوال الشخصية",
        })

    if divorce_type == "revocable":
        result["deadlines"].append({
            "name": "مدة المراجعة",
            "description": "يحق للزوج مراجعة زوجته خلال فترة العدة (المادة 91)",
            "end_date": "مع انتهاء العدة",
            "legal_basis": "المادة 91 من نظام الأحوال الشخصية",
        })

    result["notes"].append("يجب توثيق الطلاق لدى الجهة المختصة")
    return result


def _calculate_death_deadlines(date: datetime, details: dict, result: dict) -> dict:
    """Calculate death-related deadlines (widow's waiting period)."""
    is_pregnant = details.get("is_pregnant", False)

    if is_pregnant:
        result["deadlines"].append({
            "name": "عدة المتوفى عنها زوجها (حامل)",
            "description": "تنتهي العدة بوضع الحمل (المادة 120)",
            "end_date": "بوضع الحمل",
            "legal_basis": "المادة 120 من نظام الأحوال الشخصية",
        })
    else:
        # 4 months and 10 days
        iddah_end = date + timedelta(days=130)  # 4 months + 10 days
        result["deadlines"].append({
            "name": "عدة المتوفى عنها زوجها",
            "description": "أربعة أشهر وعشرة أيام (المادة 119)",
            "end_date": iddah_end.strftime("%Y-%m-%d"),
            "legal_basis": "المادة 119 من نظام الأحوال الشخصية",
        })

    result["notes"].append("تبدأ العدة من تاريخ الوفاة")
    result["notes"].append("يجب إنهاء إجراءات حصر الورثة")
    return result


def _calculate_judgment_deadlines(date: datetime, details: dict, result: dict) -> dict:
    """Calculate judgment-related deadlines."""
    # Standard appeal period: 30 days
    appeal_end = date + timedelta(days=30)
    result["deadlines"].append({
        "name": "مهلة الاعتراض على الحكم",
        "description": "ثلاثون يوماً من تاريخ تسلم صورة الحكم",
        "end_date": appeal_end.strftime("%Y-%m-%d"),
        "legal_basis": "نظام المرافعات الشرعية",
    })
    result["notes"].append("تبدأ المهلة من تاريخ تسلم صورة الحكم وليس من تاريخ صدوره")
    return result


def _calculate_custody_deadlines(date: datetime, details: dict, result: dict) -> dict:
    """Calculate custody-related deadlines."""
    child_age = details.get("child_age", 0)

    if child_age < 2:
        result["deadlines"].append({
            "name": "حضانة الأم (أقل من سنتين)",
            "description": "الحضانة للأم إذا لم يتجاوز المحضون سنتين (المادة 125)",
            "end_date": "حتى بلوغ المحضون سنتين",
            "legal_basis": "لائحة نظام الأحوال الشخصية - المادة 33",
        })

    result["deadlines"].append({
        "name": "سن تخيير المحضون",
        "description": "يخيّر المحضون عند بلوغه سن الخامسة عشرة (المادة 136)",
        "end_date": "عند بلوغ المحضون 15 سنة",
        "legal_basis": "المادة 136 من نظام الأحوال الشخصية",
    })

    return result


def _calculate_appeal_deadlines(date: datetime, details: dict, result: dict) -> dict:
    """Calculate appeal deadlines."""
    appeal_end = date + timedelta(days=30)
    result["deadlines"].append({
        "name": "مهلة الاستئناف",
        "description": "ثلاثون يوماً من تاريخ تسلم الحكم",
        "end_date": appeal_end.strftime("%Y-%m-%d"),
        "legal_basis": "نظام المرافعات الشرعية",
    })

    supreme_end = date + timedelta(days=30)
    result["deadlines"].append({
        "name": "مهلة طلب النقض",
        "description": "ثلاثون يوماً من تاريخ تبليغ حكم الاستئناف",
        "end_date": "30 يوماً من تاريخ حكم الاستئناف",
        "legal_basis": "نظام المرافعات الشرعية",
    })

    return result
