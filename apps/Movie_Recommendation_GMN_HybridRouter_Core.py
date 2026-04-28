import html
import re
import sqlite3
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from flask import render_template, request

from config import DB_PATH, DEFAULT_TOP_N

FALLBACK_MIN_RATING_COUNT = 50
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

MODEL_CONFIGS = {
    "content": {
        "label": "Blue Pill Content Signal",
        "button_prefix": "Blue Pill",
        "button_suffix": "Content Recommendation",
        "table": "user_content_recommendations_top20",
        "order_by": "recommendation_rank",
        "button_class": "is-blue-pill",
    },
    "collaborative_knn": {
        "label": "Red Pill Collaborative Recommendation",
        "button_prefix": "Red Pill",
        "button_suffix": "Collaborative Recommendation",
        "table": "user_collaborative_knn_recommendations_top20",
        "order_by": "recommendation_rank",
        "button_class": "is-red-pill",
    },
    "hybrid": {
        "label": "Purple Pill Hybrid Intelligence",
        "button_prefix": "Purple Pill",
        "button_suffix": "Hybrid Recommendation",
        "table": "user_hybrid_recommendations_top20",
        "order_by": "final_rank",
        "button_class": "is-purple-pill",
    },
}

HYBRID_APP_MODEL_CONFIGS = {
    "content": MODEL_CONFIGS["content"],
    "collaborative_knn": MODEL_CONFIGS["collaborative_knn"],
    "hybrid": MODEL_CONFIGS["hybrid"],
}

HYBRID_APP_MODEL_GROUPS = [
    {"label": "Choose Your Reality", "keys": ["content", "collaborative_knn", "hybrid"]},
]

SIMILARITY_CONFIGS = {
    "content_similarity": {
        "label": "Blue Pill Content Signal",
        "button_prefix": "Blue Pill",
        "button_suffix": "Content Recommendation",
        "table": "movie_content_similarity_top20",
        "order_by": "similarity_rank",
        "button_class": "is-blue-pill",
    },
}

COMMON_METADATA_COLUMNS = [
    "release_year",
    "genres_comma",
    "avg_rating",
    "rating_count",
    "imdb_url",
    "tmdb_url",
    "movielens_url",
]


def get_connection():
    return sqlite3.connect(DB_PATH)


def table_exists(conn, table_name):
    query = """
    SELECT 1
    FROM sqlite_master
    WHERE type IN ('table', 'view') AND name = ?
    """
    return conn.execute(query, (table_name,)).fetchone() is not None


def fetch_movie_options():
    with get_connection() as conn:
        movie_df = pd.read_sql_query(
            """
            SELECT
                movieID,
                title_clean,
                title,
                release_year
            FROM movie_content_clean
            ORDER BY title, release_year, movieID
            """,
            conn,
        )

    options = []
    for _, row in movie_df.iterrows():
        options.append(
            {
                "movieID": int(row["movieID"]),
                "label": str(row["title_clean"] or row["title"]),
            }
        )
    return options


def fetch_user_interaction_count(conn, user_id):
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM user_movie_interactions
        WHERE userID = ?
        """,
        (user_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def fetch_top_rated_fallback(conn, user_id, top_n, model_key):
    fallback_df = pd.read_sql_query(
        """
        SELECT
            ? AS userID,
            movieID AS recommended_movieID,
            title_clean AS recommended_title,
            release_year,
            genres_comma,
            avg_rating,
            rating_count,
            imdb_url,
            tmdb_url,
            movielens_url
        FROM movie_content_clean
        WHERE avg_rating IS NOT NULL
          AND rating_count >= ?
        ORDER BY avg_rating DESC, rating_count DESC, title_clean
        LIMIT ?
        """,
        conn,
        params=(user_id, FALLBACK_MIN_RATING_COUNT, top_n),
    )

    if fallback_df.empty:
        return fallback_df

    fallback_df["poster_url"] = fallback_df.apply(
        lambda row: fetch_poster_url(row.get("tmdb_url"), row.get("imdb_url")),
        axis=1,
    )

    rank_column = "final_rank" if model_key == "hybrid" else "recommendation_rank"
    fallback_df[rank_column] = range(1, len(fallback_df) + 1)
    fallback_df["model_source"] = "top_rated_fallback"

    return fallback_df


def fetch_recommendations(user_id, model_key, top_n):
    config = MODEL_CONFIGS[model_key]
    query = f"""
    SELECT *
    FROM {config['table']}
    WHERE userID = ?
    ORDER BY {config['order_by']}
    LIMIT ?
    """

    with get_connection() as conn:
        if not table_exists(conn, config["table"]):
            raise ValueError(f"Required table not found: {config['table']}")

        rec_df = pd.read_sql_query(query, conn, params=(user_id, top_n))
        if rec_df.empty:
            return fetch_top_rated_fallback(conn, user_id, top_n, model_key)

        metadata_df = pd.read_sql_query(
            """
            SELECT
                movieID,
                title_clean,
                title,
                release_year,
                genres_comma,
                avg_rating,
                rating_count,
                imdb_url,
                tmdb_url,
                movielens_url
            FROM movie_content_clean
            """,
            conn,
        )

    merged_df = rec_df.merge(
        metadata_df,
        left_on="recommended_movieID",
        right_on="movieID",
        how="left",
    )

    merged_df["poster_url"] = merged_df.apply(
        lambda row: fetch_poster_url(row.get("tmdb_url"), row.get("imdb_url")),
        axis=1,
    )

    return merged_df


def fetch_movie_similarity(movie_id, similarity_key, top_n):
    config = SIMILARITY_CONFIGS[similarity_key]
    query = f"""
    SELECT *
    FROM {config['table']}
    WHERE base_movieID = ?
    ORDER BY {config['order_by']}
    LIMIT ?
    """

    with get_connection() as conn:
        if not table_exists(conn, config["table"]):
            raise ValueError(f"Required table not found: {config['table']}")

        sim_df = pd.read_sql_query(query, conn, params=(movie_id, top_n))
        if sim_df.empty:
            return sim_df

        metadata_df = pd.read_sql_query(
            """
            SELECT
                movieID,
                title_clean,
                title,
                release_year,
                genres_comma,
                avg_rating,
                rating_count,
                imdb_url,
                tmdb_url,
                movielens_url
            FROM movie_content_clean
            """,
            conn,
        )

    merged_df = sim_df.merge(
        metadata_df,
        left_on="similar_movieID",
        right_on="movieID",
        how="left",
    )

    merged_df["poster_url"] = merged_df.apply(
        lambda row: fetch_poster_url(row.get("tmdb_url"), row.get("imdb_url")),
        axis=1,
    )

    return merged_df


def fetch_movie_summary(movie_id):
    with get_connection() as conn:
        summary_df = pd.read_sql_query(
            """
            SELECT
                movieID,
                title_clean,
                title,
                release_year,
                genres_comma
            FROM movie_content_clean
            WHERE movieID = ?
            """,
            conn,
            params=(movie_id,),
        )

    if summary_df.empty:
        return None

    row = summary_df.iloc[0]
    return {
        "movie_id": int(row["movieID"]),
        "movie_title": format_value(row.get("title_clean") or row.get("title")),
        "release_year": format_value(row.get("release_year")),
        "genere": format_value(row.get("genres_comma")),
    }


@lru_cache(maxsize=512)
def fetch_poster_url(tmdb_url, imdb_url):
    for page_url in (tmdb_url, imdb_url):
        if not page_url:
            continue

        try:
            html_text = fetch_page_html(page_url)
            poster_url = extract_meta_image(html_text)
            if poster_url:
                return poster_url
        except (HTTPError, URLError, TimeoutError, ValueError):
            continue

    return ""


@lru_cache(maxsize=512)
def fetch_page_html(url):
    req = Request(url, headers=REQUEST_HEADERS)
    with urlopen(req, timeout=10) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="ignore")


def extract_meta_image(html_text):
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE)
        if match:
            return html.unescape(match.group(1))
    return ""


def format_value(value):
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def build_table_columns(model_key):
    columns = ["poster", "display_rank", "recommended_title", "release_year", "genere"]
    if model_key == "hybrid":
        columns.append("pill_route")
    return columns


def build_table_rows(df, model_key):
    if df.empty:
        return []

    rows = []
    for _, row in df.iterrows():
        display_rank = row.get("final_rank")
        if pd.isna(display_rank):
            display_rank = row.get("recommendation_rank")

        row_dict = {
            "poster": row.get("poster_url", ""),
            "imdb_url": row.get("imdb_url", ""),
            "display_rank": format_value(display_rank),
            "recommended_title": format_value(
                row.get("title_clean") or row.get("recommended_title")
            ),
            "release_year": format_value(row.get("release_year")),
            "genere": format_value(row.get("genres_comma")),
        }

        if model_key == "hybrid":
            model_source = format_value(row.get("model_source")).strip().lower()
            badge_label = "Purple Pill"
            badge_class = "route-pill is-purple-pill"

            if model_source == "content_only":
                badge_label = "Blue Pill"
                badge_class = "route-pill is-blue-pill"
            elif model_source == "collaborative_only":
                badge_label = "Red Pill"
                badge_class = "route-pill is-red-pill"
            elif model_source == "both":
                badge_label = "Purple Pill"
                badge_class = "route-pill is-purple-pill"

            row_dict["pill_route"] = badge_label
            row_dict["pill_route_class"] = badge_class

        rows.append(row_dict)

    return rows


def build_similarity_table_columns():
    return ["poster", "display_rank", "recommended_title", "release_year", "genere"]


def build_similarity_rows(df):
    if df.empty:
        return []

    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "poster": row.get("poster_url", ""),
                "imdb_url": row.get("imdb_url", ""),
                "display_rank": format_value(row.get("similarity_rank")),
                "recommended_title": format_value(
                    row.get("title_clean") or row.get("similar_title")
                ),
                "release_year": format_value(row.get("release_year")),
                "genere": format_value(row.get("genres_comma")),
            }
        )

    return rows


def render_recommendation_app(
    template_name,
    model_configs,
    model_groups,
    default_model,
    app_title,
    app_heading,
    hero_subtitle="",
    hero_kicker="",
    allow_similarity=True,
):
    ui_focus_target = "choose_path"
    selected_mode = request.form.get(
        "mode",
        "recommendation" if not allow_similarity else "recommendation",
    ).strip()
    selected_model = request.form.get("model", default_model)
    user_id = request.form.get("user_id", "1").strip()
    top_n = request.form.get("top_n", str(DEFAULT_TOP_N)).strip()
    selected_similarity = request.form.get("similarity_model", "content_similarity").strip()
    movie_id = request.form.get("movie_id", "1").strip()
    similarity_top_n = request.form.get("similarity_top_n", str(DEFAULT_TOP_N)).strip()
    active_form = request.form.get("active_form", "")

    if selected_model not in model_configs:
        selected_model = default_model

    if not allow_similarity:
        selected_mode = "recommendation"

    results = []
    table_columns = build_table_columns(selected_model)
    similarity_results = []
    similarity_table_columns = build_similarity_table_columns()
    error_message = ""
    fallback_message = ""
    similarity_error_message = ""
    movie_options = fetch_movie_options()
    movie_summary = None
    show_rabbit_trail = False

    if request.method == "POST":
        if allow_similarity and selected_mode not in ("recommendation", "similarity"):
            selected_mode = "recommendation"
        elif not allow_similarity:
            selected_mode = "recommendation"

        if active_form == "" and selected_mode == "recommendation":
            ui_focus_target = "define_signal"
        elif active_form == "" and selected_mode == "similarity":
            ui_focus_target = "similarity_controls"

        if active_form == "recommendation_form" and selected_mode == "recommendation":
            try:
                if selected_model not in model_configs:
                    raise ValueError("Please choose a valid model.")

                parsed_user_id = int(user_id)
                parsed_top_n = int(top_n)
                if parsed_top_n <= 0:
                    raise ValueError("Top N must be greater than 0.")

                result_df = fetch_recommendations(parsed_user_id, selected_model, parsed_top_n)
                if (
                    not result_df.empty
                    and "model_source" in result_df.columns
                    and result_df["model_source"].fillna("").eq("top_rated_fallback").all()
                ):
                    fallback_message = (
                        "No personalized recommendation rows were available for this user, "
                        "so the system returned top-rated fallback movies instead."
                    )
                results = build_table_rows(result_df, selected_model)
                if not results:
                    error_message = (
                        f"No recommendations found for userID {parsed_user_id} "
                        f"using the {model_configs[selected_model]['label']} model."
                    )
            except ValueError as exc:
                error_message = str(exc)
            except sqlite3.Error as exc:
                error_message = f"SQLite error: {exc}"
            except Exception as exc:
                error_message = f"Unexpected error: {exc}"

            if error_message:
                ui_focus_target = "define_signal"
            elif selected_model == "hybrid":
                show_rabbit_trail = True
                ui_focus_target = "rabbit_trail"
            else:
                ui_focus_target = "recommendation_results"

        if allow_similarity and active_form == "similarity_form" and selected_mode == "similarity":
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
            except sqlite3.Error as exc:
                similarity_error_message = f"SQLite error: {exc}"
            except Exception as exc:
                similarity_error_message = f"Unexpected error: {exc}"

            if similarity_error_message:
                ui_focus_target = "similarity_controls"
            else:
                ui_focus_target = "similarity_results"

    return render_template(
        template_name,
        app_title=app_title,
        app_heading=app_heading,
        hero_subtitle=hero_subtitle,
        hero_kicker=hero_kicker,
        allow_similarity=allow_similarity,
        model_configs=model_configs,
        model_groups=model_groups,
        selected_mode=selected_mode,
        similarity_configs=SIMILARITY_CONFIGS,
        selected_model=selected_model,
        user_id=user_id,
        top_n=top_n,
        table_columns=table_columns,
        results=results,
        error_message=error_message,
        fallback_message=fallback_message,
        selected_similarity=selected_similarity,
        movie_id=movie_id,
        similarity_top_n=similarity_top_n,
        similarity_table_columns=similarity_table_columns,
        similarity_results=similarity_results,
        similarity_error_message=similarity_error_message,
        movie_summary=movie_summary,
        movie_options=movie_options,
        db_path=DB_PATH,
        show_rabbit_trail=show_rabbit_trail,
        ui_focus_target=ui_focus_target,
    )
