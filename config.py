LASTFM_APPLICATON_NAME = "PosterGeterinator"
LASTFM_API_KEY = "your_api_key_here"
LASTFM_SHARED_SECRET = "your_shared_secret_here"
LASTFM_ACCOUNT = "your_lastfm_account"

# ============================================================================
# Import local config overrides if they exist
# ============================================================================
try:
    from config_local import *  # noqa: F401, F403
except ImportError:
    # config_local.py doesn't exist - using defaults (expected in CI/tests)
    pass