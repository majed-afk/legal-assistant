"""
Pre-compute embeddings using Gemini API.
Uses batch_size=10 with 5s delays to respect rate limits.
765 articles ÷ 10 = ~77 batches × 5s = ~6.5 minutes.

Usage: python backend/tools/precompute_gemini.py
"""
import json
import os
import sys
import time

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_dir = os.path.dirname(project_root)

    articles_path = os.path.join(project_root, "data", "articles.json")
    embeddings_path = os.path.join(project_root, "data", "embeddings.json")

    # Load API key from .env
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: No GOOGLE_API_KEY")
        sys.exit(1)

    from google import genai
    client = genai.Client(api_key=api_key)

    # Load articles
    with open(articles_path, "r", encoding="utf-8") as f:
        articles = json.load(f)["articles"]
    total = len(articles)

    # Load existing
    existing = {}
    if os.path.exists(embeddings_path):
        try:
            with open(embeddings_path, "r") as f:
                existing = json.load(f)
        except:
            existing = {}

    missing = [a for a in articles if a["id"] not in existing]
    print(f"Total: {total} | Existing: {len(existing)} | Missing: {len(missing)}")
    sys.stdout.flush()

    if not missing:
        print("✅ Done!")
        return

    batch_size = 10
    delay = 5  # seconds between batches
    total_batches = (len(missing) + batch_size - 1) // batch_size
    start_time = time.time()

    for i in range(0, len(missing), batch_size):
        batch = missing[i:i+batch_size]
        texts = [a["text"] for a in batch]
        batch_num = i // batch_size + 1

        for attempt in range(15):
            try:
                result = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=texts,
                    config={"output_dimensionality": 768},
                )
                for article, emb in zip(batch, result.embeddings):
                    existing[article["id"]] = emb.values

                # Save after each batch
                with open(embeddings_path, "w") as f:
                    json.dump(existing, f)

                elapsed = time.time() - start_time
                pct = len(existing) / total * 100
                eta = (elapsed / max(batch_num, 1)) * (total_batches - batch_num)
                print(f"  [{batch_num}/{total_batches}] {len(existing)}/{total} ({pct:.0f}%) — ETA {eta:.0f}s")
                sys.stdout.flush()
                break

            except Exception as e:
                err = str(e)
                if "429" in err or "RATE" in err.upper() or "quota" in err.lower() or "resource" in err.lower():
                    wait = min(2 ** attempt * 5, 60)
                    print(f"  ⏳ Rate limit batch {batch_num}, wait {wait}s (attempt {attempt+1}/15)...")
                    sys.stdout.flush()
                    time.sleep(wait)
                else:
                    print(f"  ❌ Error: {e}")
                    with open(embeddings_path, "w") as f:
                        json.dump(existing, f)
                    raise
        else:
            print(f"Failed after 15 attempts. Saved {len(existing)}.")
            with open(embeddings_path, "w") as f:
                json.dump(existing, f)
            sys.exit(1)

        # Delay between batches
        if i + batch_size < len(missing):
            time.sleep(delay)

    elapsed = time.time() - start_time
    print(f"\n✅ All {len(existing)} embeddings saved in {elapsed:.0f}s!")
    size_mb = os.path.getsize(embeddings_path) / 1024 / 1024
    print(f"   Size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
