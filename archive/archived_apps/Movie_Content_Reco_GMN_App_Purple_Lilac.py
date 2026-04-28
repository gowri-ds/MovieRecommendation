from pathlib import Path

from flask import Flask

from apps.Movie_Content_Reco_GMN_HybridRouter_Core import (
    MODEL_CONFIGS,
    render_recommendation_app,
)

CONTENT_APP_MODEL_CONFIGS = {
    "content": MODEL_CONFIGS["content"],
}

CONTENT_APP_MODEL_GROUPS = [
    {"label": "Content", "keys": ["content"]},
]

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
        model_configs=CONTENT_APP_MODEL_CONFIGS,
        model_groups=CONTENT_APP_MODEL_GROUPS,
        default_model="content",
        app_title="GMN Content Recommendation System",
        app_heading="Content Based Recommendation System",
        hero_subtitle="Explore enriched content-based movie matches.",
        allow_similarity=True,
    )


if __name__ == "__main__":
    app.run(debug=True)
