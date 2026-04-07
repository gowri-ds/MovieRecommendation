"""
========================================================================
USER-LEVEL GENRE ONE-HOT RECOMMENDATION BUILD SCRIPT
========================================================================
Purpose:
    This script builds user-level recommendations using the
    movie_genre_ohe_similarity_top20 table.

What this script creates:
    Table: user_content_recommendations_genre_ohe_top20

Why this is safe:
    - It does NOT overwrite your current user_content_recommendations_top20
========================================================================
"""

import sqlite3
import traceback
from datetime import datetime

import pandas as pd


DB_PATH = r"G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db"
LIKED_RATING_THRESHOLD = 4.0
TOP_N_PER_USER = 20


def print_divider(char="=", width=72):
    print(char * width)


def table_exists(conn, object_name):
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


def detect_rating_column(conn):
    cols = get_columns(conn, "user_movie_interactions")
    candidates = ["rating", "rating_value", "user_rating"]
    for col in candidates:
        if col in cols:
            return col
    raise ValueError(
        "Could not find a rating column in user_movie_interactions."
    )


def load_user_likes(conn, rating_col, threshold):
    query = f"""
    SELECT
        userID,
        movieID,
        {rating_col} AS rating
    FROM user_movie_interactions
    WHERE {rating_col} IS NOT NULL
      AND {rating_col} >= ?
    ORDER BY userID, movieID;
    """
    return pd.read_sql_query(query, conn, params=(threshold,))


def load_all_user_seen_movies(conn):
    query = """
    SELECT DISTINCT
        userID,
        movieID
    FROM user_movie_interactions
    ORDER BY userID, movieID;
    """
    return pd.read_sql_query(query, conn)


def load_movie_similarity(conn):
    query = """
    SELECT
        base_movieID,
        base_title,
        similar_movieID,
        similar_title,
        similarity_score,
        similarity_rank
    FROM movie_genre_ohe_similarity_top20
    ORDER BY base_movieID, similarity_rank;
    """
    return pd.read_sql_query(query, conn)


def build_user_recommendations(likes_df, seen_df, similarity_df, top_n_per_user):
    candidate_df = likes_df.merge(
        similarity_df,
        left_on="movieID",
        right_on="base_movieID",
        how="inner"
    )

    candidate_df = candidate_df.rename(columns={
        "movieID": "liked_movieID",
        "rating": "liked_movie_rating"
    })

    seen_df = seen_df.rename(columns={"movieID": "recommended_movieID"})
    candidate_df = candidate_df.rename(columns={"similar_movieID": "recommended_movieID"})

    candidate_df = candidate_df.merge(
        seen_df.assign(already_seen=1),
        on=["userID", "recommended_movieID"],
        how="left"
    )

    candidate_df = candidate_df[candidate_df["already_seen"].isna()].copy()

    final_cols = [
        "userID",
        "recommended_movieID",
        "recommended_title",
        "recommendation_score",
        "supporting_liked_movies",
        "avg_supporting_rating",
        "recommendation_rank",
        "support_movie_ids",
        "support_movie_titles"
    ]

    if candidate_df.empty:
        return pd.DataFrame(columns=final_cols)

    grouped = (
        candidate_df.groupby(["userID", "recommended_movieID", "similar_title"], as_index=False)
        .agg(
            recommendation_score=("similarity_score", "sum"),
            supporting_liked_movies=("liked_movieID", "nunique"),
            avg_supporting_rating=("liked_movie_rating", "mean"),
            support_movie_ids=("liked_movieID", lambda x: ", ".join(map(str, sorted(pd.unique(x))))),
            support_movie_titles=("base_title", lambda x: ", ".join(sorted(pd.unique(x))))
        )
        .rename(columns={"similar_title": "recommended_title"})
    )

    grouped = grouped.sort_values(
        by=["userID", "recommendation_score", "supporting_liked_movies", "recommended_title"],
        ascending=[True, False, False, True]
    ).copy()

    grouped["recommendation_rank"] = grouped.groupby("userID").cumcount() + 1
    grouped = grouped[grouped["recommendation_rank"] <= top_n_per_user].copy()

    grouped["recommendation_score"] = grouped["recommendation_score"].round(6)
    grouped["avg_supporting_rating"] = grouped["avg_supporting_rating"].round(4)

    return grouped[final_cols]


def save_user_recommendation_table(conn, rec_df):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS user_content_recommendations_genre_ohe_top20;")
    cur.execute("""
        CREATE TABLE user_content_recommendations_genre_ohe_top20 (
            userID INTEGER NOT NULL,
            recommended_movieID INTEGER NOT NULL,
            recommended_title TEXT,
            recommendation_score REAL NOT NULL,
            supporting_liked_movies INTEGER NOT NULL,
            avg_supporting_rating REAL,
            recommendation_rank INTEGER NOT NULL,
            support_movie_ids TEXT,
            support_movie_titles TEXT,
            PRIMARY KEY (userID, recommendation_rank)
        );
    """)
    conn.commit()

    rec_df.to_sql("user_content_recommendations_genre_ohe_top20", conn, if_exists="append", index=False)

    cur.executescript("""
        CREATE INDEX IF NOT EXISTS idx_user_genre_ohe_recs_user
            ON user_content_recommendations_genre_ohe_top20(userID);

        CREATE INDEX IF NOT EXISTS idx_user_genre_ohe_recs_movie
            ON user_content_recommendations_genre_ohe_top20(recommended_movieID);

        CREATE INDEX IF NOT EXISTS idx_user_genre_ohe_recs_score
            ON user_content_recommendations_genre_ohe_top20(recommendation_score DESC);
    """)
    conn.commit()


def run_validation_queries(conn, top_n_per_user):
    summary = pd.read_sql_query("""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT userID) AS distinct_users,
            MIN(recommendation_rank) AS min_rank,
            MAX(recommendation_rank) AS max_rank
        FROM user_content_recommendations_genre_ohe_top20;
    """, conn)

    per_user_counts = pd.read_sql_query(f"""
        SELECT
            userID,
            COUNT(*) AS recommendation_count
        FROM user_content_recommendations_genre_ohe_top20
        GROUP BY userID
        HAVING COUNT(*) <> {top_n_per_user}
        ORDER BY userID
        LIMIT 50;
    """, conn)

    sample = pd.read_sql_query("""
        SELECT
            userID,
            recommended_movieID,
            recommended_title,
            ROUND(recommendation_score, 4) AS recommendation_score,
            supporting_liked_movies,
            ROUND(avg_supporting_rating, 2) AS avg_supporting_rating,
            recommendation_rank
        FROM user_content_recommendations_genre_ohe_top20
        WHERE userID = 1
        ORDER BY recommendation_rank
        LIMIT 10;
    """, conn)

    return summary, per_user_counts, sample


def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING USER-LEVEL GENRE ONE-HOT RECOMMENDATION BUILD")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Liked rating threshold: {LIKED_RATING_THRESHOLD}")
    print(f"Top-N recommendations per user: {TOP_N_PER_USER}")
    print(f"Run started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = None

    try:
        print("[STEP 1/6] Connecting to SQLite database...")
        conn = sqlite3.connect(DB_PATH)
        print("Success: Database connection established.\n")

        print("[STEP 2/6] Validating required source tables...")
        required_objects = ["user_movie_interactions", "movie_genre_ohe_similarity_top20"]
        missing = [obj for obj in required_objects if not table_exists(conn, obj)]
        if missing:
            raise ValueError(f"Missing required source objects: {', '.join(missing)}")
        print("Success: Required tables are present.\n")

        print("[STEP 3/6] Loading source data...")
        rating_col = detect_rating_column(conn)
        likes_df = load_user_likes(conn, rating_col, LIKED_RATING_THRESHOLD)
        seen_df = load_all_user_seen_movies(conn)
        similarity_df = load_movie_similarity(conn)

        print(f"Detected user rating column: {rating_col}")
        print(f"Liked rows loaded: {len(likes_df):,}")
        print(f"Seen rows loaded: {len(seen_df):,}")
        print(f"Similarity rows loaded: {len(similarity_df):,}\n")

        print("[STEP 4/6] Building user-level recommendations...")
        rec_df = build_user_recommendations(
            likes_df=likes_df,
            seen_df=seen_df,
            similarity_df=similarity_df,
            top_n_per_user=TOP_N_PER_USER
        )
        print(f"Recommendation rows generated: {len(rec_df):,}\n")

        print("[STEP 5/6] Saving output table...")
        save_user_recommendation_table(conn, rec_df)
        print("Success: user_content_recommendations_genre_ohe_top20 created.\n")

        print("[STEP 6/6] Running validation checks...")
        summary, per_user_counts, sample = run_validation_queries(conn, TOP_N_PER_USER)

        print("Validation summary:")
        print(summary.to_string(index=False))
        print()

        if per_user_counts.empty:
            print(f"Success: Every user has exactly {TOP_N_PER_USER} recommendations.\n")
        else:
            print("Note: Some users have fewer than Top-N recommendations.")
            print(per_user_counts.to_string(index=False))
            print()

        print("Sample recommendations for userID = 1:")
        if sample.empty:
            print("No sample rows found.")
        else:
            print(sample.to_string(index=False))
        print()

        end_time = datetime.now()
        duration = end_time - start_time

        print_divider()
        print("USER-LEVEL GENRE ONE-HOT BUILD COMPLETED SUCCESSFULLY")
        print_divider()
        print("Created table: user_content_recommendations_genre_ohe_top20")
        print("This table is separate from your current TF-IDF user recommendation table.")
        print(f"Run finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total runtime: {duration}")
        print_divider()

    except Exception as e:
        print_divider("!")
        print("USER-LEVEL GENRE ONE-HOT BUILD FAILED")
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