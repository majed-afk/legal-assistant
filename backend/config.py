import logging
import os
from dotenv import load_dotenv

load_dotenv(override=True)

_log = logging.getLogger("sanad.config")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
ARTICLES_JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "articles.json")
PDF_EXPLANATION_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "شرح نظام الأحوال الشخصية.pdf")
PDF_REGULATIONS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pdf.pdf")

# Security
API_KEY = os.getenv("API_KEY", "")  # Required API key for protected endpoints
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "100"))

# Supabase (for feedback, analytics, subscriptions)
SUPABASE_URL = os.getenv("SUPABASE_URL", os.getenv("NEXT_PUBLIC_SUPABASE_URL", ""))
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", ""))
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# Moyasar Payment Gateway
MOYASAR_SECRET_KEY = os.getenv("MOYASAR_SECRET_KEY", "")
MOYASAR_PUBLISHABLE_KEY = os.getenv("MOYASAR_PUBLISHABLE_KEY", "")
MOYASAR_CALLBACK_URL = os.getenv("MOYASAR_CALLBACK_URL", "https://sanad.audience.sa/subscription/callback")
MOYASAR_WEBHOOK_SECRET = os.getenv("MOYASAR_WEBHOOK_SECRET", "")

# PayPal Payment Gateway
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_SECRET_KEY = os.getenv("PAYPAL_SECRET_KEY", "")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")  # sandbox or live

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Startup validation warnings
def _validate_config():
    """Log warnings for missing critical environment variables."""
    if not ANTHROPIC_API_KEY:
        _log.warning("ANTHROPIC_API_KEY not set — Claude API calls will fail")
    if not SUPABASE_URL:
        _log.warning("SUPABASE_URL not set — subscriptions, feedback, analytics disabled")
    if not SUPABASE_SERVICE_KEY:
        _log.warning("SUPABASE_SERVICE_KEY not set — will fall back to anon key (reduced permissions)")
    if ENVIRONMENT == "production":
        if not MOYASAR_WEBHOOK_SECRET:
            _log.warning("MOYASAR_WEBHOOK_SECRET not set — webhook signature verification disabled in production!")
        if not API_KEY:
            _log.warning("API_KEY not set — legacy API key auth disabled")

_validate_config()
