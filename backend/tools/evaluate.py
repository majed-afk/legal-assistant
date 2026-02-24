#!/usr/bin/env python3
"""
نظام تقييم تلقائي للمستشار القانوني الذكي
Automated evaluation benchmark for the Saudi Legal AI Assistant.

Tests:
1. Topic Detection — Does the pipeline detect the right topic from a query?
2. Article Retrieval — Does the RAG return the correct articles?
3. End-to-End — Does the full system give a correct answer?

Usage:
    python -m backend.tools.evaluate                    # Run all tests
    python -m backend.tools.evaluate --test topics      # Topic detection only
    python -m backend.tools.evaluate --test retrieval   # Article retrieval only
    python -m backend.tools.evaluate --test e2e         # End-to-end (requires API)
    python -m backend.tools.evaluate --test e2e --api   # Test against deployed API
"""

import json
import os
import sys
import time
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

# ──────────────────────────────────────────────────────────────
# TEST CASES — Benchmark questions with expected outcomes
# ──────────────────────────────────────────────────────────────

TOPIC_TESTS = [
    # === أحوال شخصية ===
    # فصحى
    {"query": "ما شروط عقد الزواج؟", "expected_topics": ["عقد الزواج"], "lang": "formal"},
    {"query": "ما أحكام الطلاق الرجعي؟", "expected_topics": ["الطلاق"], "lang": "formal"},
    {"query": "كيف تُحسب نفقة الأولاد؟", "expected_topics": ["النفقة"], "lang": "formal"},
    {"query": "ما ترتيب أصحاب الحق في الحضانة؟", "expected_topics": ["الحضانة"], "lang": "formal"},
    {"query": "ما شروط صحة الوصية؟", "expected_topics": ["الوصية"], "lang": "formal"},
    {"query": "كيف تُقسم التركة بين الورثة؟", "expected_topics": ["أحكام الإرث"], "lang": "formal"},
    {"query": "ما أحكام الخلع في النظام؟", "expected_topics": ["الخلع"], "lang": "formal"},
    {"query": "ما حقوق الزوجة على زوجها؟", "expected_topics": ["حقوق الزوجين"], "lang": "formal"},
    {"query": "كيف يثبت النسب؟", "expected_topics": ["النسب"], "lang": "formal"},
    {"query": "ما أحكام المهر المسمى والمثل؟", "expected_topics": ["المهر"], "lang": "formal"},
    {"query": "ما هي العدة وأنواعها؟", "expected_topics": ["العدة"], "lang": "formal"},
    {"query": "أحكام الرضاع في النظام", "expected_topics": ["المحرمات"], "lang": "formal"},
    {"query": "ما هو الحجب في الميراث؟", "expected_topics": ["التعصيب"], "lang": "formal"},

    # عامي
    {"query": "ابي اتزوج وش الشروط؟", "expected_topics": ["عقد الزواج"], "lang": "colloquial"},
    {"query": "زوجي طلقني وش حقوقي؟", "expected_topics": ["الطلاق"], "lang": "colloquial"},
    {"query": "مطلقة وابي نفقة عيالي", "expected_topics": ["النفقة", "نفقة الأقارب"], "lang": "colloquial"},
    {"query": "مانعتني أشوف عيالي", "expected_topics": ["الحضانة"], "lang": "colloquial"},
    {"query": "أبوي مات وش نصيبي من الورث؟", "expected_topics": ["أحكام الإرث"], "lang": "colloquial"},
    {"query": "يضربني ويهينني أبي أفسخ", "expected_topics": ["فسخ النكاح"], "lang": "colloquial"},
    {"query": "زوجي ما يصرف علي", "expected_topics": ["النفقة"], "lang": "colloquial"},
    {"query": "كم مهري لو ما اتفقنا؟", "expected_topics": ["المهر"], "lang": "colloquial"},
    {"query": "طلقني بالواتساب هل يعتبر؟", "expected_topics": ["الطلاق"], "lang": "colloquial"},
    {"query": "أنا معلقة زوجي لا طلق ولا أمسك", "expected_topics": ["فسخ النكاح"], "lang": "colloquial"},
    {"query": "عيالي عند أمهم وتبي تسافر فيهم", "expected_topics": ["الحضانة"], "lang": "colloquial"},
    {"query": "خطيبي رجع عن الخطبة أبي هداياي", "expected_topics": ["الخطبة"], "lang": "colloquial"},

    # === نظام الإثبات ===
    {"query": "ما شروط الإقرار القضائي؟", "expected_topics": ["إقرار"], "lang": "formal"},
    {"query": "ما حجية الشهادة في الإثبات؟", "expected_topics": ["شهادة"], "lang": "formal"},
    {"query": "أحكام اليمين في نظام الإثبات", "expected_topics": ["يمين"], "lang": "formal"},
    {"query": "ما هي القرائن القضائية؟", "expected_topics": ["قرائن"], "lang": "formal"},
    {"query": "أحكام الخبرة في الإثبات", "expected_topics": ["خبرة"], "lang": "formal"},

    # === نظام المرافعات ===
    {"query": "كيف أرفع دعوى في المحكمة؟", "expected_topics": ["رفع الدعوى"], "lang": "formal"},
    {"query": "ما هي مواعيد الاستئناف؟", "expected_topics": ["مرافعات - أحكام ختامية"], "lang": "formal"},
    {"query": "أحكام التبليغ في المرافعات", "expected_topics": ["مرافعات - أحكام عامة"], "lang": "formal"},
]

ARTICLE_RETRIEVAL_TESTS = [
    # question, expected article numbers (at least one should appear in results)
    {"query": "ما تعريف الزواج؟", "expected_articles": [6], "law": "أحوال"},
    {"query": "سن الزواج في النظام", "expected_articles": [9], "law": "أحوال"},
    {"query": "أحكام المهر", "expected_articles": [36, 37, 38, 39, 40, 41], "law": "أحوال"},
    {"query": "نفقة الزوجة", "expected_articles": [45, 46, 47], "law": "أحوال"},
    {"query": "حالات الطلاق", "expected_articles": [77, 78, 79, 80, 81, 82, 83], "law": "أحوال"},
    {"query": "الحضانة بعد الطلاق", "expected_articles": [125, 126, 127, 128], "law": "أحوال"},
    {"query": "مدة أكثر الحمل", "expected_articles": [68], "law": "أحوال"},
    {"query": "غياب الزوج وطلب الفسخ", "expected_articles": [114], "law": "أحوال"},
    {"query": "سن انتهاء الحضانة", "expected_articles": [135], "law": "أحوال"},
    {"query": "الوصية لوارث", "expected_articles": [179, 190], "law": "أحوال"},
    {"query": "أسباب الإرث", "expected_articles": [199, 200], "law": "أحوال"},
    {"query": "طلاق الهازل", "expected_articles": [83], "law": "أحوال"},
]

E2E_TESTS = [
    {
        "query": "ما هي مدة أكثر الحمل في النظام؟",
        "must_contain": ["عشرة", "أشهر", "68"],
        "must_not_contain": ["سنة", "365"],
        "description": "مدة الحمل — يجب أن تكون 10 أشهر وليس سنة",
    },
    {
        "query": "زوجي مسافر من سنة ونص ومالي خبر عنه، هل أقدر أطلب تفريق؟",
        "must_contain": ["أربعة", "أشهر", "114"],
        "must_not_contain": [],
        "description": "غيبة الزوج — المدة 4 أشهر وليس سنة",
    },
    {
        "query": "متى تنتهي الحضانة؟",
        "must_contain": ["ثمانية عشر", "135"],
        "must_not_contain": [],
        "description": "انتهاء الحضانة — عمر 18 وليس 15",
    },
    {
        "query": "ما شروط عقد الزواج؟",
        "must_contain": ["إيجاب", "قبول"],
        "must_not_contain": [],
        "description": "أركان عقد الزواج",
    },
    {
        "query": "طلقني بالثلاث بكلمة وحدة",
        "must_contain": ["طلقة واحدة", "83"],
        "must_not_contain": [],
        "description": "الطلاق بالثلاث يقع واحدة",
    },
]


# ──────────────────────────────────────────────────────────────
# TEST RUNNERS
# ──────────────────────────────────────────────────────────────

def run_topic_tests():
    """Test topic detection from the RAG pipeline."""
    from backend.rag.pipeline import _detect_topics

    print("\n" + "=" * 60)
    print("🎯 اختبار كشف الموضوعات (Topic Detection)")
    print("=" * 60)

    passed = 0
    failed = 0
    results = []

    for test in TOPIC_TESTS:
        query = test["query"]
        expected = set(test["expected_topics"])
        lang = test["lang"]

        detected = set(_detect_topics(query))
        # Check if at least one expected topic was detected
        match = bool(expected & detected)

        if match:
            passed += 1
            status = "✅"
        else:
            failed += 1
            status = "❌"

        results.append({
            "query": query,
            "expected": list(expected),
            "detected": list(detected),
            "passed": match,
            "lang": lang,
        })

        if not match:
            print(f"  {status} [{lang[:4]}] {query[:50]}")
            print(f"       متوقع: {expected} | مكتشف: {detected}")

    total = passed + failed
    pct = (passed / total * 100) if total else 0

    print(f"\n📊 النتيجة: {passed}/{total} ({pct:.0f}%)")
    print(f"   فصحى: {sum(1 for r in results if r['passed'] and r['lang'] == 'formal')}/{sum(1 for r in results if r['lang'] == 'formal')}")
    print(f"   عامي: {sum(1 for r in results if r['passed'] and r['lang'] == 'colloquial')}/{sum(1 for r in results if r['lang'] == 'colloquial')}")

    return {"test": "topic_detection", "passed": passed, "total": total, "pct": pct, "details": results}


def run_retrieval_tests():
    """Test article retrieval from the RAG pipeline."""
    from backend.rag.pipeline import retrieve_context

    print("\n" + "=" * 60)
    print("📚 اختبار استرجاع المواد (Article Retrieval)")
    print("=" * 60)

    passed = 0
    failed = 0
    results = []

    for test in ARTICLE_RETRIEVAL_TESTS:
        query = test["query"]
        expected_articles = set(test["expected_articles"])

        # Get retrieved context
        context = retrieve_context(query)

        # Extract article numbers from context
        retrieved_nums = set()
        for match in re.findall(r'المادة[:\s]+(\d+)', context):
            retrieved_nums.add(int(match))
        # Also check for "المادة (X)" format
        for match in re.findall(r'المادة\s*\((\d+)\)', context):
            retrieved_nums.add(int(match))
        # Check for article_number in the raw text
        for match in re.findall(r'"article_number":\s*(\d+)', context):
            retrieved_nums.add(int(match))

        # At least one expected article should be in retrieved
        hit = bool(expected_articles & retrieved_nums)

        if hit:
            passed += 1
            status = "✅"
        else:
            failed += 1
            status = "❌"
            print(f"  {status} {query[:50]}")
            print(f"       متوقع: {expected_articles} | مسترجع: {retrieved_nums}")

        results.append({
            "query": query,
            "expected": list(expected_articles),
            "retrieved": list(retrieved_nums),
            "passed": hit,
        })

    total = passed + failed
    pct = (passed / total * 100) if total else 0
    print(f"\n📊 النتيجة: {passed}/{total} ({pct:.0f}%)")

    return {"test": "article_retrieval", "passed": passed, "total": total, "pct": pct, "details": results}


def run_e2e_tests(api_url: str = None):
    """Run end-to-end tests against the full system."""
    print("\n" + "=" * 60)
    print("🔄 اختبار شامل (End-to-End)")
    print("=" * 60)

    if api_url:
        print(f"   🌐 API: {api_url}")
    else:
        # Use local imports
        from backend.services.legal_assistant import get_legal_response
        print("   💻 محلي (local)")

    passed = 0
    failed = 0
    results = []

    for test in E2E_TESTS:
        query = test["query"]
        must_contain = test["must_contain"]
        must_not_contain = test["must_not_contain"]
        desc = test["description"]

        print(f"\n  📝 {desc}")
        print(f"     سؤال: {query}")

        try:
            if api_url:
                resp = requests.post(
                    f"{api_url}/api/chat",
                    json={"message": query, "conversation_id": f"eval_{int(time.time())}"},
                    headers={"X-API-Key": os.getenv("API_KEY", "")},
                    timeout=60,
                )
                if resp.status_code == 200:
                    answer = resp.json().get("response", "")
                else:
                    answer = f"ERROR {resp.status_code}: {resp.text[:200]}"
            else:
                answer = get_legal_response(query)

            # Check must_contain
            missing = [w for w in must_contain if w not in answer]
            # Check must_not_contain
            found_bad = [w for w in must_not_contain if w in answer]

            test_passed = len(missing) == 0 and len(found_bad) == 0

            if test_passed:
                passed += 1
                print(f"     ✅ نجح")
            else:
                failed += 1
                if missing:
                    print(f"     ❌ ناقص: {missing}")
                if found_bad:
                    print(f"     ❌ يحتوي خطأ: {found_bad}")

            results.append({
                "query": query,
                "description": desc,
                "passed": test_passed,
                "missing": missing,
                "found_bad": found_bad,
                "answer_preview": answer[:200] if answer else "NO RESPONSE",
            })

            time.sleep(1)  # Rate limiting

        except Exception as e:
            failed += 1
            print(f"     ❌ خطأ: {e}")
            results.append({
                "query": query,
                "description": desc,
                "passed": False,
                "error": str(e),
            })

    total = passed + failed
    pct = (passed / total * 100) if total else 0
    print(f"\n📊 النتيجة: {passed}/{total} ({pct:.0f}%)")

    return {"test": "end_to_end", "passed": passed, "total": total, "pct": pct, "details": results}


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

import re

def main():
    parser = argparse.ArgumentParser(description="Legal AI Evaluation System")
    parser.add_argument("--test", choices=["topics", "retrieval", "e2e", "all"], default="all")
    parser.add_argument("--api", type=str, default="", help="API URL for e2e tests (e.g., https://...onrender.com)")
    parser.add_argument("--output", type=str, default="", help="Save results to JSON file")
    args = parser.parse_args()

    print("⚖️  نظام تقييم المستشار القانوني الذكي")
    print("=" * 60)

    all_results = []

    if args.test in ("topics", "all"):
        all_results.append(run_topic_tests())

    if args.test in ("retrieval", "all"):
        all_results.append(run_retrieval_tests())

    if args.test in ("e2e", "all"):
        api_url = args.api or None
        all_results.append(run_e2e_tests(api_url))

    # Summary
    print("\n" + "=" * 60)
    print("📊 الملخص النهائي")
    print("=" * 60)

    total_passed = sum(r["passed"] for r in all_results)
    total_tests = sum(r["total"] for r in all_results)
    overall_pct = (total_passed / total_tests * 100) if total_tests else 0

    for r in all_results:
        icon = "✅" if r["pct"] >= 90 else "🟡" if r["pct"] >= 70 else "❌"
        print(f"  {icon} {r['test']}: {r['passed']}/{r['total']} ({r['pct']:.0f}%)")

    print(f"\n  📊 الإجمالي: {total_passed}/{total_tests} ({overall_pct:.0f}%)")
    grade = "A+" if overall_pct >= 95 else "A" if overall_pct >= 90 else "B" if overall_pct >= 80 else "C" if overall_pct >= 70 else "D"
    print(f"  🏆 التقدير: {grade}")

    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = ROOT / "backend" / "data" / "eval_results.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_passed": total_passed,
                "total_tests": total_tests,
                "overall_pct": overall_pct,
                "grade": grade,
            },
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n  📁 النتائج محفوظة: {output_path}")

    return 0 if overall_pct >= 80 else 1


if __name__ == "__main__":
    sys.exit(main())
