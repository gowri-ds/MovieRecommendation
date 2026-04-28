from pathlib import Path

from flask import Flask

from Movie_Recommendation_GMN_HybridRouter_Core import (
    HYBRID_APP_MODEL_CONFIGS,
    HYBRID_APP_MODEL_GROUPS,
    render_recommendation_app,
)
from config import FLASK_DEBUG, HYBRID_APP_TITLE

PROJECT_ROOT = Path(__file__).resolve().parents[1]

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static"),
)


@app.route("/", methods=["GET", "POST"])
def index():
    return render_recommendation_app(
        template_name="index.html",
        model_configs=HYBRID_APP_MODEL_CONFIGS,
        model_groups=HYBRID_APP_MODEL_GROUPS,
        default_model="hybrid",
        app_title=HYBRID_APP_TITLE,
        app_heading=HYBRID_APP_TITLE,
        hero_subtitle="Beneath every choice lies a pattern.",
        allow_similarity=True,
    )


if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG)
