from pathlib import Path

from flask import Flask, render_template, request

from apps.Movie_Content_Reco_GMN_HybridRouter_Core import (
    MODEL_CONFIGS,
    render_recommendation_app,
)

COLLABORATIVE_APP_MODEL_CONFIGS = {
    "collaborative_knn": MODEL_CONFIGS["collaborative_knn"],
}

COLLABORATIVE_APP_MODEL_GROUPS = [
    {"label": "Collaborative", "keys": ["collaborative_knn"]},
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
        template_name="matrix_index.html",
        model_configs=COLLABORATIVE_APP_MODEL_CONFIGS,
        model_groups=COLLABORATIVE_APP_MODEL_GROUPS,
        default_model="collaborative_knn",
        app_title="Matrix Matchmakers Collaborative Reco",
        app_heading="Collaborative Movie Recommendation",
        hero_subtitle="Surface recommendations from shared user behavior patterns.",
        hero_kicker="Matrix Matchmakers",
        allow_similarity=False,
    )


if __name__ == "__main__":
    app.run(debug=True)
