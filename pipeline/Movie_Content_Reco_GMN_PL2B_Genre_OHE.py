"""
========================================================================
GENRE ONE-HOT CONTENT SIMILARITY BUILD SCRIPT
========================================================================
Purpose:
    This script builds a movie-to-movie similarity model using
    genre one-hot encoding instead of TF-IDF text features.

What this script creates:
    Table: movie_genre_ohe_similarity_top20

Why this is safe:
    - It does NOT overwrite your TF-IDF tables
    - It creates a separate parallel model for comparison
========================================================================
"""

import sqlite3
import traceback
from datetime import datetime

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


# ---------------------------------------------------------------------
# USER SETTINGS
# ---------------------------------------------------------------------
DB_PATH = r"G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db"
TOP_N = 20


# ---------------------------------------------------------------------
# HELPER
# ---------------------------------------------------------------------
def print_divider(char="=", width=72):
    print(char * width)


def table_or_view_exists(conn, object_name):
    query = """
    SELECT name
    FROM sqlite_master
    WHERE type IN ('table', 'view')
      AND name = ?;
    """
    row = conn.execute(query, (object_name,)).fetchone()
    return row is not None


def get_columns(conn, object_name):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({object_name});")
    return [row[1] for row in cur.fetchall()]


def get_source_table_or_view(conn):
    """
    Prefer vw_movie_content_features, then fallback to movie_content_clean.
    We need movieID, title, and either genres_pipe or genres.
    """
    checks = [
        "vw_movie_content_features",
        "movie_content_clean"
    ]

    for object_name in checks:
        if table_or_view_exists(conn, object_name):
            cols = get_columns(conn, object_name)
            if "movieID" in cols and "title" in cols and ("genres_pipe" in cols or "genres" in cols):
                return object_name

    raise ValueError(
        "Could not find a usable source object. Expected vw_movie_content_features "
        "or movie_content_clean with movieID, title, and genres_pipe/genres."
    )


def load_movie_genres(conn):
    source_name = get_source_table_or_view(conn)
    cols = get_columns(conn, source_name)

    genre_col = "genres_pipe" if "genres_pipe" in cols else "genres"

    query = f"""
    SELECT
        movieID,
        title,
        {genre_col} AS genres_pipe
    FROM {source_name}
    WHERE {genre_col} IS NOT NULL
      AND TRIM({genre_col}) <> ''
    ORDER BY movieID;
    """

    df = pd.read_sql_query(query, conn)
    return df, source_name


def clean_and_split_genres(genres_value):
    if pd.isna(genres_value):
        return []

    genres = [g.strip().lower() for g in str(genres_value).split("|") if g.strip()]
    genres = [g for g in genres if g != "(no genres listed)"]
    return genres


def build_genre_ohe_matrix(movies_df):
    """
    Build one-hot encoded genre matrix.
    """
    movies_df = movies_df.copy()
    movies_df["genre_list"] = movies_df["genres_pipe"].apply(clean_and_split_genres)

    # Remove movies with no usable genres
    movies_df = movies_df[movies_df["genre_list"].map(len) > 0].copy()

    all_genres = sorted(set(g for row in movies_df["genre_list"] for g in row))

    for genre in all_genres:
        movies_df[f"genre_{genre.replace('-', '_').replace(' ', '_')}"] = (
            movies_df["genre_list"].apply(lambda x: 1 if genre in x else 0)
        )

    # Exclude the helper list column and keep only numeric one-hot features.
    feature_cols = [
        c for c in movies_df.columns
        if c.startswith("genre_") and c != "genre_list"
    ]
    feature_matrix = movies_df[feature_cols]

    return movies_df, feature_matrix, all_genres


def build_similarity_rows(movies_df, feature_matrix, top_n=20):
    cosine_sim = cosine_similarity(feature_matrix)

    rows = []
    movie_ids = movies_df["movieID"].tolist()
    titles = movies_df["title"].tolist()

    for i, base_movie_id in enumerate(movie_ids):
        scores = list(enumerate(cosine_sim[i]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        top_matches = [(j, score) for j, score in scores if j != i][:top_n]

        for rank, (j, score) in enumerate(top_matches, start=1):
            rows.append({
                "base_movieID": int(base_movie_id),
                "base_title": titles[i],
                "similar_movieID": int(movie_ids[j]),
                "similar_title": titles[j],
                "similarity_score": float(score),
                "similarity_rank": int(rank)
            })

    return pd.DataFrame(rows)


def save_similarity_table(conn, sim_df):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS movie_genre_ohe_similarity_top20;")
    cur.execute("""
        CREATE TABLE movie_genre_ohe_similarity_top20 (
            base_movieID INTEGER NOT NULL,
            base_title TEXT,
            similar_movieID INTEGER NOT NULL,
            similar_title TEXT,
            similarity_score REAL NOT NULL,
            similarity_rank INTEGER NOT NULL,
            PRIMARY KEY (base_movieID, similarity_rank)
        );
    """)
    conn.commit()

    sim_df.to_sql("movie_genre_ohe_similarity_top20", conn, if_exists="append", index=False)

    cur.executescript("""
        CREATE INDEX IF NOT EXISTS idx_genre_ohe_base_movie
            ON movie_genre_ohe_similarity_top20(base_movieID);

        CREATE INDEX IF NOT EXISTS idx_genre_ohe_similar_movie
            ON movie_genre_ohe_similarity_top20(similar_movieID);

        CREATE INDEX IF NOT EXISTS idx_genre_ohe_score
            ON movie_genre_ohe_similarity_top20(similarity_score DESC);
    """)
    conn.commit()


def run_validation_queries(conn):
    summary = pd.read_sql_query("""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT base_movieID) AS distinct_base_movies,
            MIN(similarity_rank) AS min_rank,
            MAX(similarity_rank) AS max_rank
        FROM movie_genre_ohe_similarity_top20;
    """, conn)

    exceptions = pd.read_sql_query(f"""
        SELECT
            base_movieID,
            base_title,
            COUNT(*) AS recommendation_count
        FROM movie_genre_ohe_similarity_top20
        GROUP BY base_movieID, base_title
        HAVING COUNT(*) <> {TOP_N}
        ORDER BY base_movieID;
    """, conn)

    sample = pd.read_sql_query("""
        SELECT
            base_movieID,
            base_title,
            similar_movieID,
            similar_title,
            ROUND(similarity_score, 4) AS similarity_score,
            similarity_rank
        FROM movie_genre_ohe_similarity_top20
        WHERE base_movieID = 1
        ORDER BY similarity_rank
        LIMIT 10;
    """, conn)

    return summary, exceptions, sample


def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING GENRE ONE-HOT MOVIE SIMILARITY BUILD")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Top-N similar movies per movie: {TOP_N}")
    print(f"Run started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = None

    try:
        print("[STEP 1/5] Connecting to SQLite database...")
        conn = sqlite3.connect(DB_PATH)
        print("Success: Database connection established.\n")

        print("[STEP 2/5] Loading movie genre data...")
        movies_df, source_name = load_movie_genres(conn)
        print(f"Success: Source object found -> {source_name}")
        print(f"Movies loaded: {len(movies_df):,}\n")

        print("[STEP 3/5] Building genre one-hot matrix...")
        movies_df, feature_matrix, all_genres = build_genre_ohe_matrix(movies_df)
        print(f"Usable movies after genre cleaning: {len(movies_df):,}")
        print(f"Unique genres encoded: {len(all_genres)}")
        print(f"Genres found: {', '.join(all_genres)}\n")

        if movies_df.empty:
            raise ValueError("No movies with usable genres were found.")

        print("[STEP 4/5] Computing cosine similarity and Top-N results...")
        sim_df = build_similarity_rows(movies_df, feature_matrix, TOP_N)
        print(f"Similarity rows generated: {len(sim_df):,}")

        save_similarity_table(conn, sim_df)
        print("Success: movie_genre_ohe_similarity_top20 created.\n")

        print("[STEP 5/5] Running validation checks...")
        summary, exceptions, sample = run_validation_queries(conn)

        print("Validation summary:")
        print(summary.to_string(index=False))
        print()

        if exceptions.empty:
            print(f"Success: Every base movie has exactly {TOP_N} recommendations.\n")
        else:
            print("Warning: Some movies do not have the expected recommendation count.")
            print(exceptions.head(20).to_string(index=False))
            print()

        print("Sample recommendations for base_movieID = 1:")
        if sample.empty:
            print("No sample rows found.")
        else:
            print(sample.to_string(index=False))
        print()

        end_time = datetime.now()
        duration = end_time - start_time

        print_divider()
        print("GENRE ONE-HOT BUILD COMPLETED SUCCESSFULLY")
        print_divider()
        print("Created table: movie_genre_ohe_similarity_top20")
        print("This table is separate from your TF-IDF similarity table.")
        print(f"Run finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total runtime: {duration}")
        print_divider()

    except Exception as e:
        print_divider("!")
        print("GENRE ONE-HOT BUILD FAILED")
        print_divider("!")
        print("Error details:")
        print(str(e))
        print()
        print(traceback.format_exc())
        print_divider("!")
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
