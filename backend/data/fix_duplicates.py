"""
Fix duplicate text in articles extracted from PDF.
The PDF has two text layers causing every phrase to appear twice consecutively.
"""
import json
import re
import os

ARTICLES_PATH = os.path.join(os.path.dirname(__file__), "articles.json")


def normalize(text):
    """Remove spaces, diacritics, tatweel for comparison."""
    return re.sub(r'[\s\u0640\u064B-\u065F\u0670]', '', text)


def deduplicate_pdf_text(text):
    """Remove duplicate text from PDF with double text layers."""
    lines = text.split('\n')
    cleaned = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove duplicate page numbers like ٣١٣١ -> ٣١
        line = re.sub(r'([٠-٩]{2,4})\1', r'\1', line)

        words = line.split()
        n = len(words)

        if n < 3:
            cleaned.append(line)
            continue

        # Try to split the line into two halves where second = duplicate of first
        best = None
        for mid in range(max(1, n // 3), min(n, 2 * n // 3 + 1)):
            part1 = ' '.join(words[:mid])
            part2 = ' '.join(words[mid:])
            if normalize(part1) == normalize(part2) and len(normalize(part1)) > 2:
                best = part1
                break

        if best is None:
            # Try word-level duplicate removal
            best = remove_short_dups(line)

        cleaned.append(best)

    # Second pass: remove consecutive duplicate lines
    final = []
    for line in cleaned:
        if final and normalize(final[-1]) == normalize(line):
            continue
        final.append(line)

    # Third pass: handle concatenated words (e.g. "تعريفالخطبة تعريف" -> "تعريف الخطبة")
    # and short duplicates with punctuation
    result = '\n'.join(final)

    # Remove patterns like ":الشرح: الشرح" -> ":الشرح"
    # Pattern: punctuation + words + same punctuation + same words
    result = re.sub(
        r'([:\.،؛]\s*)([^\n:\.،؛]{2,40}?)\1\2',
        r'\1\2',
        result
    )

    return result


def remove_short_dups(line):
    """Remove consecutive duplicate word sequences within a line."""
    words = line.split()
    result = []
    i = 0
    while i < len(words):
        found = False
        for slen in range(min(20, (len(words) - i) // 2), 0, -1):
            if i + slen * 2 > len(words):
                continue
            s1 = words[i:i + slen]
            s2 = words[i + slen:i + slen * 2]
            n1 = normalize(' '.join(s1))
            n2 = normalize(' '.join(s2))
            if n1 == n2 and len(n1) > 2:
                result.extend(s1)
                i += slen * 2
                found = True
                break
        if not found:
            result.append(words[i])
            i += 1
    return ' '.join(result)


def fix_all_articles():
    """Fix duplicate text in all articles and rebuild ChromaDB."""
    with open(ARTICLES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = 0
    fixed = 0
    total_orig_chars = 0
    total_fixed_chars = 0

    for article in data['articles']:
        total += 1
        original_text = article['text']
        cleaned_text = deduplicate_pdf_text(original_text)

        total_orig_chars += len(original_text)
        total_fixed_chars += len(cleaned_text)

        if len(cleaned_text) < len(original_text) * 0.95:
            article['text'] = cleaned_text
            fixed += 1

    # Save
    with open(ARTICLES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    reduction = (1 - total_fixed_chars / total_orig_chars) * 100
    print(f"Fixed {fixed}/{total} articles")
    print(f"Total reduction: {total_orig_chars:,} -> {total_fixed_chars:,} chars ({reduction:.0f}%)")


if __name__ == '__main__':
    fix_all_articles()
