from pathlib import Path

from flask import Flask, render_template, request

from Movie_Content_Reco_GMN_App_Purple_Lilac import (
    DB_PATH,
    DEFAULT_TOP_N,
    MODEL_CONFIGS,
    MODEL_GROUPS,
    SIMILARITY_CONFIGS,
    build_similarity_rows,
    build_similarity_table_columns,
    build_table_columns,
    build_table_rows,
    fetch_movie_options,
    fetch_movie_similarity,
    fetch_movie_summary,
    fetch_recommendations,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static"),
)


@app.route("/", methods=["GET", "POST"])
def index():
    selected_mode = request.form.get("mode", "recommendation").strip()
    selected_model = request.form.get("model", "tfidf")
    user_id = request.form.get("user_id", "1").strip()
    top_n = request.form.get("top_n", str(DEFAULT_TOP_N)).strip()
    selected_similarity = request.form.get("similarity_model", "tfidf_similarity").strip()
    movie_id = request.form.get("movie_id", "1").strip()
    similarity_top_n = request.form.get("similarity_top_n", str(DEFAULT_TOP_N)).strip()
    active_form = request.form.get("active_form", "")

    results = []
    table_columns = build_table_columns(selected_model)
    similarity_results = []
    similarity_table_columns = build_similarity_table_columns()
    error_message = ""
    similarity_error_message = ""
    movie_options = fetch_movie_options()
    movie_summary = None

    if request.method == "POST":
        if selected_mode not in ("recommendation", "similarity"):
            selected_mode = "recommendation"

        if active_form in ("", "recommendation_form") and selected_mode == "recommendation":
            try:
                if selected_model not in MODEL_CONFIGS:
                    raise ValueError("Please choose a valid model.")

                parsed_user_id = int(user_id)
                parsed_top_n = int(top_n)
                if parsed_top_n <= 0:
                    raise ValueError("Top N must be greater than 0.")

                result_df = fetch_recommendations(parsed_user_id, selected_model, parsed_top_n)
                results = build_table_rows(result_df, selected_model)
                if not results:
                    error_message = (
                        f"No recommendations found for userID {parsed_user_id} "
                        f"using the {MODEL_CONFIGS[selected_model]['label']} model."
                    )
            except ValueError as exc:
                error_message = str(exc)
            except Exception as exc:
                error_message = f"Unexpected error: {exc}"

        if active_form == "similarity_form" and selected_mode == "similarity":
            try:
                if selected_similarity not in SIMILARITY_CONFIGS:
                    raise ValueError("Please choose a valid similarity model.")

                parsed_movie_id = int(movie_id)
                parsed_similarity_top_n = int(similarity_top_n)
                if parsed_similarity_top_n <= 0:
                    raise ValueError("Similarity Top N must be greater than 0.")

                similarity_df = fetch_movie_similarity(
                    parsed_movie_id,
                    selected_similarity,
                    parsed_similarity_top_n,
                )
                movie_summary = fetch_movie_summary(parsed_movie_id)
                similarity_results = build_similarity_rows(similarity_df)
                if not similarity_results:
                    similarity_error_message = (
                        f"No similar movies found for movieID {parsed_movie_id} "
                        f"using {SIMILARITY_CONFIGS[selected_similarity]['label']}."
                    )
            except ValueError as exc:
                similarity_error_message = str(exc)
            except Exception as exc:
                similarity_error_message = f"Unexpected error: {exc}"

    return render_template(
        "matrix_index.html",
        model_configs=MODEL_CONFIGS,
        model_groups=MODEL_GROUPS,
        selected_mode=selected_mode,
        similarity_configs=SIMILARITY_CONFIGS,
        selected_model=selected_model,
        user_id=user_id,
        top_n=top_n,
        table_columns=table_columns,
        results=results,
        error_message=error_message,
        selected_similarity=selected_similarity,
        movie_id=movie_id,
        similarity_top_n=similarity_top_n,
        similarity_table_columns=similarity_table_columns,
        similarity_results=similarity_results,
        similarity_error_message=similarity_error_message,
        movie_summary=movie_summary,
        movie_options=movie_options,
        db_path=DB_PATH,
    )


if __name__ == "__main__":
    app.run(debug=True)
