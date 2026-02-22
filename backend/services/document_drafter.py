"""
Legal document drafting templates and service.
"""
from __future__ import annotations

DRAFT_TYPES = {
    "lawsuit": {
        "name_ar": "لائحة دعوى",
        "name_en": "Lawsuit Filing",
        "required_fields": ["plaintiff_name", "defendant_name", "case_type", "facts", "requests"],
    },
    "memo": {
        "name_ar": "مذكرة قانونية",
        "name_en": "Legal Memo",
        "required_fields": ["case_number", "case_type", "arguments"],
    },
    "appeal": {
        "name_ar": "لائحة اعتراض (استئناف)",
        "name_en": "Appeal Filing",
        "required_fields": ["judgment_number", "judgment_date", "appeal_grounds"],
    },
    "response": {
        "name_ar": "مذكرة جوابية",
        "name_en": "Response Memo",
        "required_fields": ["case_number", "response_to", "arguments"],
    },
    "khula": {
        "name_ar": "طلب خلع",
        "name_en": "Khula Request",
        "required_fields": ["wife_name", "husband_name", "reasons", "compensation_offer"],
    },
    "custody": {
        "name_ar": "طلب حضانة",
        "name_en": "Custody Request",
        "required_fields": ["parent_name", "children_names", "children_ages", "reasons"],
    },
    "nafaqa": {
        "name_ar": "طلب نفقة",
        "name_en": "Alimony Request",
        "required_fields": ["claimant_name", "defendant_name", "relationship", "amount_requested"],
    },
}


def get_draft_types() -> list[dict]:
    """Return available draft types."""
    return [
        {"type": k, "name_ar": v["name_ar"], "name_en": v["name_en"], "required_fields": v["required_fields"]}
        for k, v in DRAFT_TYPES.items()
    ]


def validate_draft_request(draft_type: str, case_details: dict) -> tuple[bool, str]:
    """Validate that required fields are present."""
    if draft_type not in DRAFT_TYPES:
        return False, f"نوع المذكرة غير معروف: {draft_type}"

    required = DRAFT_TYPES[draft_type]["required_fields"]
    missing = [f for f in required if f not in case_details or not case_details[f]]

    if missing:
        return False, f"حقول مطلوبة ناقصة: {', '.join(missing)}"

    return True, ""


def build_drafting_prompt(draft_type: str, case_details: dict) -> str:
    """Build a prompt for Claude to draft the document."""
    type_info = DRAFT_TYPES.get(draft_type, {})
    type_name = type_info.get("name_ar", draft_type)

    details_text = "\n".join(f"- {k}: {v}" for k, v in case_details.items() if v)

    return f"""أحتاج صياغة {type_name} في قضية أحوال شخصية.

تفاصيل القضية:
{details_text}

أرجو صياغة {type_name} كاملة مع الاستناد إلى مواد نظام الأحوال الشخصية."""
