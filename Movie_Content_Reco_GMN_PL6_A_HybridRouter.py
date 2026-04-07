"""
========================================================================
HYBRID RECOMMENDATION ROUTER BUILD SCRIPT
========================================================================
Purpose:
    This script combines the TF-IDF recommendation model and the
    genre one-hot encoding recommendation model into a single
    hybrid recommendation table.

What this script creates:
    Table: user_hybrid_recommendations_top20

Why this is useful:
    - Keeps the richer TF-IDF signal
    - Adds genre-based support from the OHE model
    - Rewards overlap when both models recommend the same movie
========================================================================
"""

import sqlite3
import traceback
from datetime import datetime

import pandas as pd


DB_PATH = r"G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db"
TOP_N_PER_USER = 20
TFIDF_WEIGHT = 0.7
OHE_WEIGHT = 0.3
OVERLAP_BONUS = 0.05


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


def _validate_weights(tfidf_weight, ohe_weight):
    if tfidf_weight < 0 or ohe_weight < 0:
        raise ValueError("Model weights must be non-negative.")
    if tfidf_weight == 0 and ohe_weight == 0:
        raise ValueError("At least one model weight must be greater than 0.")


def _normalize_scores(df, score_col, normalized_col):
    if df.empty:
        df = df.copy()
        df[normalized_col] = pd.Series(dtype=float)
        return df

    df = df.copy()
    max_score = df[score_col].max()
    if pd.isna(max_score) or max_score <= 0:
        df[normalized_col] = 0.0
    else:
        df[normalized_col] = df[score_col] / max_score

    return df


def _empty_hybrid_frame():
    return pd.DataFrame(
        columns=[
            "userID",
            "recommended_movieID",
            "recommended_title",
            "tfidf_score",
            "ohe_score",
            "tfidf_score_norm",
            "ohe_score_norm",
            "recommended_by_both",
            "final_score",
            "model_source",
            "final_rank",
        ]
    )


def get_routed_recommendations(
    user_id,
    db_path,
    top_n=10,
    tfidf_weight=0.7,
    ohe_weight=0.3,
    overlap_bonus=0.05,
):
    """
    Get final routed recommendations for a user by combining:
    1. TF-IDF recommendation model
    2. Genre OHE recommendation model
    """
    if top_n <= 0:
        raise ValueError("top_n must be greater than 0.")

    _validate_weights(tfidf_weight, ohe_weight)

    tfidf_query = """
    SELECT
        userID,
        recommended_movieID,
        recommended_title,
        recommendation_score AS tfidf_score
    FROM user_content_recommendations_top20
    WHERE userID = ?
    """

    ohe_query = """
    SELECT
        userID,
        recommended_movieID,
        recommended_title,
        recommendation_score AS ohe_score
    FROM user_content_recommendations_genre_ohe_top20
    WHERE userID = ?
    """

    with sqlite3.connect(db_path) as conn:
        tfidf_df = pd.read_sql_query(tfidf_query, conn, params=(user_id,))
        ohe_df = pd.read_sql_query(ohe_query, conn, params=(user_id,))

    return build_hybrid_for_user(
        tfidf_df=tfidf_df,
        ohe_df=ohe_df,
        top_n=top_n,
        tfidf_weight=tfidf_weight,
        ohe_weight=ohe_weight,
        overlap_bonus=overlap_bonus,
    )


def build_hybrid_for_user(
    tfidf_df,
    ohe_df,
    top_n,
    tfidf_weight,
    ohe_weight,
    overlap_bonus,
):
    tfidf_df = _normalize_scores(tfidf_df, "tfidf_score", "tfidf_score_norm")
    ohe_df = _normalize_scores(ohe_df, "ohe_score", "ohe_score_norm")

    final_df = pd.merge(
        tfidf_df,
        ohe_df,
        on=["userID", "recommended_movieID", "recommended_title"],
        how="outer",
    )

    if final_df.empty:
        return _empty_hybrid_frame()

    final_df["tfidf_score"] = final_df["tfidf_score"].fillna(0.0)
    final_df["ohe_score"] = final_df["ohe_score"].fillna(0.0)
    final_df["tfidf_score_norm"] = final_df["tfidf_score_norm"].fillna(0.0)
    final_df["ohe_score_norm"] = final_df["ohe_score_norm"].fillna(0.0)

    final_df["recommended_by_both"] = (
        (final_df["tfidf_score"] > 0) & (final_df["ohe_score"] > 0)
    ).astype(int)

    final_df["final_score"] = (
        tfidf_weight * final_df["tfidf_score_norm"]
        + ohe_weight * final_df["ohe_score_norm"]
        + overlap_bonus * final_df["recommended_by_both"]
    )

    def model_source(row):
        if row["tfidf_score"] > 0 and row["ohe_score"] > 0:
            return "both"
        if row["tfidf_score"] > 0:
            return "tfidf_only"
        return "ohe_only"

    final_df["model_source"] = final_df.apply(model_source, axis=1)

    final_df = final_df.sort_values(
        by=[
            "final_score",
            "recommended_by_both",
            "tfidf_score_norm",
            "ohe_score_norm",
            "recommended_title",
        ],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)

    final_df["final_rank"] = final_df.index + 1

    final_cols = [
        "userID",
        "recommended_movieID",
        "recommended_title",
        "tfidf_score",
        "ohe_score",
        "tfidf_score_norm",
        "ohe_score_norm",
        "recommended_by_both",
        "final_score",
        "model_source",
        "final_rank",
    ]
    return final_df[final_cols].head(top_n)


def load_all_model_recommendations(conn):
    tfidf_query = """
    SELECT
        userID,
        recommended_movieID,
        recommended_title,
        recommendation_score AS tfidf_score
    FROM user_content_recommendations_top20
    ORDER BY userID, recommendation_rank;
    """

    ohe_query = """
    SELECT
        userID,
        recommended_movieID,
        recommended_title,
        recommendation_score AS ohe_score
    FROM user_content_recommendations_genre_ohe_top20
    ORDER BY userID, recommendation_rank;
    """

    tfidf_df = pd.read_sql_query(tfidf_query, conn)
    ohe_df = pd.read_sql_query(ohe_query, conn)
    return tfidf_df, ohe_df


def build_hybrid_recommendation_table(
    tfidf_df,
    ohe_df,
    top_n_per_user,
    tfidf_weight,
    ohe_weight,
    overlap_bonus,
):
    user_ids = sorted(set(tfidf_df["userID"]).union(set(ohe_df["userID"])))
    all_user_frames = []

    for user_id in user_ids:
        user_tfidf = tfidf_df[tfidf_df["userID"] == user_id].copy()
        user_ohe = ohe_df[ohe_df["userID"] == user_id].copy()

        user_hybrid = build_hybrid_for_user(
            tfidf_df=user_tfidf,
            ohe_df=user_ohe,
            top_n=top_n_per_user,
            tfidf_weight=tfidf_weight,
            ohe_weight=ohe_weight,
            overlap_bonus=overlap_bonus,
        )

        if not user_hybrid.empty:
            all_user_frames.append(user_hybrid)

    if not all_user_frames:
        return _empty_hybrid_frame()

    return pd.concat(all_user_frames, ignore_index=True)


def save_hybrid_table(conn, hybrid_df):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS user_hybrid_recommendations_top20;")
    cur.execute(
        """
        CREATE TABLE user_hybrid_recommendations_top20 (
            userID INTEGER NOT NULL,
            recommended_movieID INTEGER NOT NULL,
            recommended_title TEXT,
            tfidf_score REAL NOT NULL,
            ohe_score REAL NOT NULL,
            tfidf_score_norm REAL NOT NULL,
            ohe_score_norm REAL NOT NULL,
            recommended_by_both INTEGER NOT NULL,
            final_score REAL NOT NULL,
            model_source TEXT NOT NULL,
            final_rank INTEGER NOT NULL,
            PRIMARY KEY (userID, final_rank)
        );
        """
    )
    conn.commit()

    hybrid_df.to_sql(
        "user_hybrid_recommendations_top20",
        conn,
        if_exists="append",
        index=False,
    )

    cur.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_user_hybrid_recs_user
            ON user_hybrid_recommendations_top20(userID);

        CREATE INDEX IF NOT EXISTS idx_user_hybrid_recs_movie
            ON user_hybrid_recommendations_top20(recommended_movieID);

        CREATE INDEX IF NOT EXISTS idx_user_hybrid_recs_score
            ON user_hybrid_recommendations_top20(final_score DESC);
        """
    )
    conn.commit()


def run_validation_queries(conn, top_n_per_user):
    summary = pd.read_sql_query(
        """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT userID) AS distinct_users,
            MIN(final_rank) AS min_rank,
            MAX(final_rank) AS max_rank,
            ROUND(AVG(final_score), 4) AS avg_final_score,
            ROUND(AVG(recommended_by_both), 4) AS share_recommended_by_both
        FROM user_hybrid_recommendations_top20;
        """,
        conn,
    )

    per_user_counts = pd.read_sql_query(
        f"""
        SELECT
            userID,
            COUNT(*) AS recommendation_count
        FROM user_hybrid_recommendations_top20
        GROUP BY userID
        HAVING COUNT(*) <> {top_n_per_user}
        ORDER BY userID
        LIMIT 50;
        """,
        conn,
    )

    source_mix = pd.read_sql_query(
        """
        SELECT
            model_source,
            COUNT(*) AS row_count
        FROM user_hybrid_recommendations_top20
        GROUP BY model_source
        ORDER BY row_count DESC;
        """,
        conn,
    )

    sample = pd.read_sql_query(
        """
        SELECT
            userID,
            recommended_movieID,
            recommended_title,
            ROUND(tfidf_score, 4) AS tfidf_score,
            ROUND(ohe_score, 4) AS ohe_score,
            ROUND(final_score, 4) AS final_score,
            model_source,
            final_rank
        FROM user_hybrid_recommendations_top20
        WHERE userID = 1
        ORDER BY final_rank
        LIMIT 10;
        """,
        conn,
    )

    return summary, per_user_counts, source_mix, sample


def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING HYBRID RECOMMENDATION ROUTER BUILD")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Top-N recommendations per user: {TOP_N_PER_USER}")
    print(f"TF-IDF weight: {TFIDF_WEIGHT}")
    print(f"Genre OHE weight: {OHE_WEIGHT}")
    print(f"Overlap bonus: {OVERLAP_BONUS}")
    print(f"Run started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = None

    try:
        print("[STEP 1/5] Connecting to SQLite database...")
        conn = sqlite3.connect(DB_PATH)
        print("Success: Database connection established.")
        print()

        print("[STEP 2/5] Validating required source tables...")
        required_objects = [
            "user_content_recommendations_top20",
            "user_content_recommendations_genre_ohe_top20",
        ]
        missing = [obj for obj in required_objects if not table_exists(conn, obj)]
        if missing:
            raise ValueError(f"Missing required source objects: {', '.join(missing)}")
        print("Success: Required tables are present.")
        print()

        print("[STEP 3/5] Loading source recommendation tables...")
        tfidf_df, ohe_df = load_all_model_recommendations(conn)
        print(f"TF-IDF recommendation rows loaded: {len(tfidf_df):,}")
        print(f"Genre OHE recommendation rows loaded: {len(ohe_df):,}")
        print(
            f"Distinct users across both models: "
            f"{len(sorted(set(tfidf_df['userID']).union(set(ohe_df['userID'])))):,}"
        )
        print()

        print("[STEP 4/5] Building hybrid recommendations...")
        hybrid_df = build_hybrid_recommendation_table(
            tfidf_df=tfidf_df,
            ohe_df=ohe_df,
            top_n_per_user=TOP_N_PER_USER,
            tfidf_weight=TFIDF_WEIGHT,
            ohe_weight=OHE_WEIGHT,
            overlap_bonus=OVERLAP_BONUS,
        )
        print(f"Hybrid recommendation rows generated: {len(hybrid_df):,}")
        print()

        print("[STEP 5/5] Saving output table and validating results...")
        save_hybrid_table(conn, hybrid_df)
        summary, per_user_counts, source_mix, sample = run_validation_queries(
            conn, TOP_N_PER_USER
        )

        print("Validation summary:")
        print(summary.to_string(index=False))
        print()

        if per_user_counts.empty:
            print(f"Success: Every user has exactly {TOP_N_PER_USER} recommendations.")
        else:
            print("Warning: Some users do not have the expected recommendation count.")
            print(per_user_counts.to_string(index=False))
        print()

        print("Model source mix:")
        print(source_mix.to_string(index=False))
        print()

        print("Sample hybrid recommendations for userID = 1:")
        if sample.empty:
            print("No sample rows found for userID = 1.")
        else:
            print(sample.to_string(index=False))
        print()

        end_time = datetime.now()
        duration = end_time - start_time

        print_divider()
        print("HYBRID ROUTER BUILD COMPLETED SUCCESSFULLY")
        print_divider()
        print("Created table: user_hybrid_recommendations_top20")
        print("This table combines the TF-IDF and genre OHE user recommendation tables.")
        print(f"Run finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total runtime: {duration}")
        print_divider()

    except Exception as e:
        print_divider("!")
        print("HYBRID ROUTER BUILD FAILED")
        print_divider("!")
        print("Error details:")
        print(str(e))
        print()
        print("Full traceback for debugging:")
        print(traceback.format_exc())
        print_divider("!")
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
