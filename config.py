import os


PROJECT_NAME = "GMN Recommendation Pipeline"
HYBRID_APP_TITLE = "Matrix Matchmakers"

DB_PATH = os.getenv(
    "GMN_DB_PATH",
    r"G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db",
)
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "YOUR_TMDB_API_KEY_HERE")
HF_TOKEN = os.getenv("HF_TOKEN", "")
DEFAULT_TOP_N = int(os.getenv("GMN_DEFAULT_TOP_N", "10"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
