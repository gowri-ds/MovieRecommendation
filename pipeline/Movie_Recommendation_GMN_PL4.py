
"""
========================================================================
USER-LEVEL CONTENT RECOMMENDATION BUILD SCRIPT
========================================================================
Purpose:
    This script builds user-level content recommendations by combining:
        1. The user's liked/rated movies from user_movie_interactions
        2. The movie-to-movie similarity table movie_content_similarity_top20

What this script creates:
    Table: user_content_recommendations_top20

What this table contains:
    - userID                    : the user receiving recommendations
    - recommended_movieID       : the recommended movie
    - recommended_title         : the recommended movie title
    - recommendation_score      : summed similarity score from supporting movies
    - supporting_liked_movies   : how many liked movies supported this recommendation
    - avg_supporting_rating     : average rating the user gave to the supporting movies
    - recommendation_rank       : rank within each user
    - support_movie_ids         : comma-separated movieIDs that supported the recommendation
    - support_movie_titles      : comma-separated titles of supporting movies

Logic:
    Step 1:
        Find movies a user liked.
        Default rule: rating >= 4.0

    Step 2:
        For each liked movie, look up its Top-20 similar movies.

    Step 3:
        Remove movies the user has already interacted with, so we do not
        recommend something they already rated/tagged.

    Step 4:
        Aggregate candidate recommendations at the user level and rank them.

Why this is useful:
    This is the next layer after movie-to-movie similarity.
    It turns "movies similar to X" into "movies recommended for user U".

Before running:
    Make sure these already exist in SQLite:
        - user_movie_interactions
        - movie_content_similarity_top20

Python packages needed:
    - pandas
========================================================================
"""

import sqlite3
import traceback
from datetime import datetime

import pandas as pd

from config import DB_PATH

# ---------------------------------------------------------------------
# USER SETTINGS
# ---------------------------------------------------------------------
LIKED_RATING_THRESHOLD = 4.0
TOP_N_PER_USER = 20


# ---------------------------------------------------------------------
# HELPER: pretty divider for readable console output
# ---------------------------------------------------------------------
def print_divider(char="=", width=72):
    print(char * width)


# ---------------------------------------------------------------------
# HELPER: check whether a table exists
# ---------------------------------------------------------------------
def table_exists(conn, object_name):
    query = """
    SELECT name
    FROM sqlite_master
    WHERE type IN ('table', 'view')
      AND name = ?;
    """
    row = conn.execute(query, (object_name,)).fetchone()
    return row is not None


# ---------------------------------------------------------------------
# HELPER: get the column names of a table
# ---------------------------------------------------------------------
def get_columns(conn, object_name):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({object_name});")
    return [row[1] for row in cur.fetchall()]


# ---------------------------------------------------------------------
# HELPER: detect the rating column in user_movie_interactions
# Why this exists:
#   Different builds sometimes use rating, user_rating, or rating_value.
#   This keeps the script flexible for new users.
# ---------------------------------------------------------------------
def detect_rating_column(conn):
    cols = get_columns(conn, "user_movie_interactions")
    candidates = ["rating", "rating_value", "user_rating"]
    for col in candidates:
        if col in cols:
            return col
    raise ValueError(
        "Could not find a rating column in user_movie_interactions. "
        "Expected one of: rating, rating_value, user_rating."
    )


# ---------------------------------------------------------------------
# LOAD USER LIKED MOVIES
# Why this exists:
#   Pull only the movies a user liked strongly enough to act as preference
#   signals for content-based recommendation.
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# LOAD ALL USER INTERACTIONS
# Why this exists:
#   We need to exclude already-seen movies from final recommendations.
# ---------------------------------------------------------------------
def load_all_user_seen_movies(conn):
    query = """
    SELECT DISTINCT
        userID,
        movieID
    FROM user_movie_interactions
    ORDER BY userID, movieID;
    """
    return pd.read_sql_query(query, conn)


# ---------------------------------------------------------------------
# LOAD MOVIE-TO-MOVIE CONTENT SIMILARITY
# ---------------------------------------------------------------------
def load_movie_similarity(conn):
    query = """
    SELECT
        base_movieID,
        base_title,
        similar_movieID,
        similar_title,
        similarity_score,
        similarity_rank
    FROM movie_content_similarity_top20
    ORDER BY base_movieID, similarity_rank;
    """
    return pd.read_sql_query(query, conn)


# ---------------------------------------------------------------------
# BUILD USER RECOMMENDATIONS
# Why this exists:
#   Joins user liked movies with similar movies, removes seen movies,
#   aggregates support, and ranks top recommendations per user.
# ---------------------------------------------------------------------
def build_user_recommendations(likes_df, seen_df, similarity_df, top_n_per_user):
    # Join liked movies to similar movies
    candidate_df = likes_df.merge(
        similarity_df,
        left_on="movieID",
        right_on="base_movieID",
        how="inner"
    )

    # Rename for clarity
    candidate_df = candidate_df.rename(columns={
        "movieID": "liked_movieID",
        "rating": "liked_movie_rating"
    })

    # Remove recommendations for movies the user has already seen
    seen_df = seen_df.rename(columns={"movieID": "recommended_movieID"})
    candidate_df = candidate_df.rename(columns={"similar_movieID": "recommended_movieID"})

    candidate_df = candidate_df.merge(
        seen_df.assign(already_seen=1),
        on=["userID", "recommended_movieID"],
        how="left"
    )

    candidate_df = candidate_df[candidate_df["already_seen"].isna()].copy()

    # If nothing survives the filter, return an empty frame with final columns
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

    # Aggregate recommendation support at user + candidate movie level
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

    # Rank within each user
    grouped = grouped.sort_values(
        by=["userID", "recommendation_score", "supporting_liked_movies", "recommended_title"],
        ascending=[True, False, False, True]
    ).copy()

    grouped["recommendation_rank"] = (
        grouped.groupby("userID").cumcount() + 1
    )

    grouped = grouped[grouped["recommendation_rank"] <= top_n_per_user].copy()

    # Friendly numeric cleanup
    grouped["recommendation_score"] = grouped["recommendation_score"].round(6)
    grouped["avg_supporting_rating"] = grouped["avg_supporting_rating"].round(4)

    return grouped[final_cols]


# ---------------------------------------------------------------------
# SAVE TO SQLITE
# ---------------------------------------------------------------------
def save_user_recommendation_table(conn, rec_df):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS user_content_recommendations_top20;")
    cur.execute("""
        CREATE TABLE user_content_recommendations_top20 (
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

    rec_df.to_sql("user_content_recommendations_top20", conn, if_exists="append", index=False)

    cur.executescript("""
        CREATE INDEX IF NOT EXISTS idx_user_recs_user
            ON user_content_recommendations_top20(userID);

        CREATE INDEX IF NOT EXISTS idx_user_recs_movie
            ON user_content_recommendations_top20(recommended_movieID);

        CREATE INDEX IF NOT EXISTS idx_user_recs_score
            ON user_content_recommendations_top20(recommendation_score DESC);
    """)
    conn.commit()


# ---------------------------------------------------------------------
# VALIDATION CHECKS
# ---------------------------------------------------------------------
def run_validation_queries(conn, top_n_per_user):
    summary = pd.read_sql_query("""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT userID) AS distinct_users,
            MIN(recommendation_rank) AS min_rank,
            MAX(recommendation_rank) AS max_rank
        FROM user_content_recommendations_top20;
    """, conn)

    per_user_counts = pd.read_sql_query(f"""
        SELECT
            userID,
            COUNT(*) AS recommendation_count
        FROM user_content_recommendations_top20
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
        FROM user_content_recommendations_top20
        WHERE userID = 1
        ORDER BY recommendation_rank
        LIMIT 10;
    """, conn)

    return summary, per_user_counts, sample


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING USER-LEVEL CONTENT RECOMMENDATION BUILD")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Liked rating threshold: {LIKED_RATING_THRESHOLD}")
    print(f"Top-N recommendations per user: {TOP_N_PER_USER}")
    print(f"Run started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = None

    try:
        # STEP 1: connect
        print("[STEP 1/6] Connecting to SQLite database...")
        conn = sqlite3.connect(DB_PATH)
        print("Success: Database connection established.")
        print()

        # STEP 2: validate source tables
        print("[STEP 2/6] Validating required source tables...")
        required_objects = ["user_movie_interactions", "movie_content_similarity_top20"]
        missing = [obj for obj in required_objects if not table_exists(conn, obj)]
        if missing:
            raise ValueError(f"Missing required source objects: {', '.join(missing)}")
        print("Success: Required tables are present.")
        print()

        # STEP 3: load source data
        print("[STEP 3/6] Loading source data...")
        rating_col = detect_rating_column(conn)
        likes_df = load_user_likes(conn, rating_col, LIKED_RATING_THRESHOLD)
        seen_df = load_all_user_seen_movies(conn)
        similarity_df = load_movie_similarity(conn)

        print(f"Detected user rating column: {rating_col}")
        print(f"Liked user-movie rows loaded: {len(likes_df):,}")
        print(f"Seen user-movie rows loaded: {len(seen_df):,}")
        print(f"Movie similarity rows loaded: {len(similarity_df):,}")
        print()

        if likes_df.empty:
            raise ValueError(
                f"No user likes found at threshold >= {LIKED_RATING_THRESHOLD}. "
                f"Try lowering the threshold."
            )

        print("Preview of liked-movie input:")
        print(likes_df.head(5).to_string(index=False))
        print()

        # STEP 4: build recommendations
        print("[STEP 4/6] Building user-level recommendations...")
        rec_df = build_user_recommendations(
            likes_df=likes_df,
            seen_df=seen_df,
            similarity_df=similarity_df,
            top_n_per_user=TOP_N_PER_USER
        )
        print("Success: User recommendation aggregation completed.")
        print(f"Recommendation rows generated: {len(rec_df):,}")
        print()

        # STEP 5: save output table
        print("[STEP 5/6] Writing results to SQLite table user_content_recommendations_top20...")
        save_user_recommendation_table(conn, rec_df)
        print("Success: User recommendation table created and indexed.")
        print()

        # STEP 6: validation
        print("[STEP 6/6] Running validation checks...")
        summary, per_user_counts, sample = run_validation_queries(conn, TOP_N_PER_USER)

        print("Validation summary:")
        print(summary.to_string(index=False))
        print()

        if per_user_counts.empty:
            print(f"Success: Every user has exactly {TOP_N_PER_USER} recommendations.")
        else:
            print("Note: Some users have fewer than the requested Top-N recommendations.")
            print("This usually happens because they have seen too many candidate movies")
            print("or do not have enough strong liked-movie support.")
            print(per_user_counts.to_string(index=False))
        print()

        print("Sample recommendations for userID = 1:")
        if sample.empty:
            print("No sample rows found for userID = 1.")
        else:
            print(sample.to_string(index=False))
        print()

        end_time = datetime.now()
        duration = end_time - start_time

        print_divider()
        print("USER RECOMMENDATION BUILD COMPLETED SUCCESSFULLY")
        print_divider()
        print("What this script has done:")
        print(f"1. Connected to your SQLite database at:")
        print(f"   {DB_PATH}")
        print("2. Read the user's liked movies from:")
        print("   user_movie_interactions")
        print("3. Read movie-to-movie content similarity from:")
        print("   movie_content_similarity_top20")
        print(f"4. Treated ratings >= {LIKED_RATING_THRESHOLD} as liked movies")
        print("5. Pulled similar movies for each liked movie")
        print("6. Excluded movies the user has already seen or rated")
        print("7. Aggregated recommendation support across multiple liked movies")
        print(f"8. Kept the Top {TOP_N_PER_USER} recommendations per user")
        print("9. Created the SQLite output table:")
        print("   user_content_recommendations_top20")
        print("10. Added indexes so future SQL queries run faster")
        print("11. Ran validation checks to confirm the build completed correctly")
        print()
        print("What you can do next:")
        print(" - Query top recommendations for any userID")
        print(" - Inspect support_movie_titles to explain why a movie was recommended")
        print(" - Tune the liked rating threshold")
        print(" - Tune the number of recommendations per user")
        print()
        print(f"Run finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total runtime: {duration}")
        print_divider()

    except Exception as e:
        print_divider("!")
        print("USER RECOMMENDATION BUILD FAILED")
        print_divider("!")
        print("Error details:")
        print(str(e))
        print()
        print("Full traceback for debugging:")
        print(traceback.format_exc())
        print()
        print("Most likely things to check:")
        print(" - Is the database path correct?")
        print(" - Does user_movie_interactions exist?")
        print(" - Does movie_content_similarity_top20 exist?")
        print(" - Does user_movie_interactions have a rating column?")
        print(" - Did the movie-to-movie content script run successfully first?")
        print_divider("!")
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
