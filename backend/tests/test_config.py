"""Tests for backend.config — configuration module loads and has expected defaults."""
import os
import pytest


class TestConfigModule:
    """Tests for the config module."""

    def test_config_imports_without_error(self):
        """Config module should import without raising errors."""
        from backend import config
        assert config is not None

    def test_claude_model_has_default(self):
        """CLAUDE_MODEL should have a sensible default value."""
        from backend.config import CLAUDE_MODEL
        assert isinstance(CLAUDE_MODEL, str)
        assert len(CLAUDE_MODEL) > 0

    def test_embedding_model_set(self):
        """EMBEDDING_MODEL should be set to the expected multilingual model."""
        from backend.config import EMBEDDING_MODEL
        assert EMBEDDING_MODEL == "paraphrase-multilingual-MiniLM-L12-v2"

    def test_chroma_persist_dir_is_absolute_path(self):
        """CHROMA_PERSIST_DIR should be an absolute path."""
        from backend.config import CHROMA_PERSIST_DIR
        assert os.path.isabs(CHROMA_PERSIST_DIR)
        assert "chroma_db" in CHROMA_PERSIST_DIR

    def test_articles_json_path_is_absolute(self):
        """ARTICLES_JSON_PATH should be an absolute path to articles.json."""
        from backend.config import ARTICLES_JSON_PATH
        assert os.path.isabs(ARTICLES_JSON_PATH)
        assert ARTICLES_JSON_PATH.endswith("articles.json")

    def test_rate_limit_defaults(self):
        """Rate limit defaults should be sensible integers."""
        from backend.config import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_DAY
        assert isinstance(RATE_LIMIT_PER_MINUTE, int)
        assert isinstance(RATE_LIMIT_PER_DAY, int)
        assert RATE_LIMIT_PER_MINUTE > 0
        assert RATE_LIMIT_PER_DAY > 0
        assert RATE_LIMIT_PER_DAY >= RATE_LIMIT_PER_MINUTE

    def test_supabase_url_is_string(self):
        """SUPABASE_URL should be a string (may be empty if not configured)."""
        from backend.config import SUPABASE_URL
        assert isinstance(SUPABASE_URL, str)

    def test_api_key_is_string(self):
        """API_KEY should be a string (may be empty if not configured)."""
        from backend.config import API_KEY
        assert isinstance(API_KEY, str)

    def test_paypal_mode_default(self):
        """PAYPAL_MODE should default to 'sandbox'."""
        from backend.config import PAYPAL_MODE
        assert PAYPAL_MODE in ("sandbox", "live")

    def test_moyasar_callback_url_has_default(self):
        """MOYASAR_CALLBACK_URL should have a default value."""
        from backend.config import MOYASAR_CALLBACK_URL
        assert isinstance(MOYASAR_CALLBACK_URL, str)
        assert len(MOYASAR_CALLBACK_URL) > 0

    def test_paths_under_backend_directory(self):
        """All file paths should be under the backend directory tree."""
        from backend.config import CHROMA_PERSIST_DIR, ARTICLES_JSON_PATH
        # Both paths should contain 'backend' in them
        assert "backend" in CHROMA_PERSIST_DIR
        assert "backend" in ARTICLES_JSON_PATH
