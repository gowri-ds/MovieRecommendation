import html
from pathlib import Path
import re
import sqlite3
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from flask import Flask, render_template, request


DB_PATH = r"G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db"
DEFAULT_TOP_N = 10
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

MODEL_CONFIGS = {
    "tfidf": {
        "label": "TF-IDF Model",
        "table": "user_content_recommendations_top20",
        "order_by": "recommendation_rank",
    },
    "genre_ohe": {
        "label": "Genre OHE Model",
        "table": "user_content_recommendations_genre_ohe_top20",
        "order_by": "recommendation_rank",
    },
    "hybrid": {
        "label": "Weighted Hybrid Router",
        "table": "user_hybrid_recommendations_top20",
        "order_by": "final_rank",
    },
    "confidence": {
        "label": "Confidence Hybrid Router",
        "table": "user_confidence_hybrid_recommendations_top20",
        "order_by": "final_rank",
    },
}

MODEL_GROUPS = [
    {
        "label": "Models",
        "keys": ["tfidf", "genre_ohe"],
    },
    {
        "label": "Routers",
        "keys": ["hybrid", "confidence"],
    },
]

SIMILARITY_CONFIGS = {
    "tfidf_similarity": {
        "label": "TF-IDF",
        "table": "movie_content_similarity_top20",
        "order_by": "similarity_rank",
    },
    "genre_ohe_similarity": {
        "label": "Genre OHE",
        "table": "movie_genre_ohe_similarity_top20",
        "order_by": "similarity_rank",
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static"),
)


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
            return rec_df

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
    return ["poster", "display_rank", "recommended_title", "release_year", "genere"]


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
            except sqlite3.Error as exc:
                error_message = f"SQLite error: {exc}"
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
            except sqlite3.Error as exc:
                similarity_error_message = f"SQLite error: {exc}"
            except Exception as exc:
                similarity_error_message = f"Unexpected error: {exc}"

    return render_template(
        "index.html",
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
