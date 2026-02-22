import os
from dotenv import load_dotenv

load_dotenv(override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
ARTICLES_JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "articles.json")
PDF_EXPLANATION_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "شرح نظام الأحوال الشخصية.pdf")
PDF_REGULATIONS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pdf.pdf")
