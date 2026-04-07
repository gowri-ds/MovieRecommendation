"""
========================================================================
CONFIDENCE-BASED HYBRID ROUTER BUILD SCRIPT
========================================================================
Purpose:
    This script combines the TF-IDF and Genre OHE user recommendation
    tables into a confidence-routed final recommendation table.

What this script creates:
    Table: user_confidence_hybrid_recommendations_top20

Why this is useful:
    - Trusts TF-IDF more when its score is strong
    - Falls back to Genre OHE when TF-IDF is missing
    - Rewards overlap when both models recommend the same movie
========================================================================
"""

import sqlite3
import traceback
from datetime import datetime

import pandas as pd


DB_PATH = r"G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db"
TOP_N_PER_USER = 20
TFIDF_WEIGHT_STRONG = 0.80
TFIDF_WEIGHT_MEDIUM = 0.65
OHE_WEIGHT_STRONG = 0.20
OHE_WEIGHT_MEDIUM = 0.35
BOTH_BONUS = 0.08
TFIDF_STRONG_THRESHOLD = 0.50
TFIDF_MEDIUM_THRESHOLD = 0.20
OHE_ONLY_PENALTY = 0.85


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


def _empty_confidence_frame():
    return pd.DataFrame(
        columns=[
            "final_rank",
            "userID",
            "recommended_movieID",
            "recommended_title",
            "tfidf_score",
            "ohe_score",
            "recommended_by_both",
            "model_source",
            "confidence_bucket",
            "confidence_label",
            "final_score",
        ]
    )


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


def get_confidence_routed_recommendations(
    user_id,
    db_path,
    top_n=10,
    tfidf_weight_strong=0.80,
    tfidf_weight_medium=0.65,
    ohe_weight_strong=0.20,
    ohe_weight_medium=0.35,
    both_bonus=0.08,
    tfidf_strong_threshold=0.50,
    tfidf_medium_threshold=0.20,
    ohe_only_penalty=0.85
):
    """
    Confidence-based router for final movie recommendations.
    """
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

    return build_confidence_routed_for_user(
        tfidf_df=tfidf_df,
        ohe_df=ohe_df,
        top_n=top_n,
        tfidf_weight_strong=tfidf_weight_strong,
        tfidf_weight_medium=tfidf_weight_medium,
        ohe_weight_strong=ohe_weight_strong,
        ohe_weight_medium=ohe_weight_medium,
        both_bonus=both_bonus,
        tfidf_strong_threshold=tfidf_strong_threshold,
        tfidf_medium_threshold=tfidf_medium_threshold,
        ohe_only_penalty=ohe_only_penalty,
    )


def build_confidence_routed_for_user(
    tfidf_df,
    ohe_df,
    top_n,
    tfidf_weight_strong,
    tfidf_weight_medium,
    ohe_weight_strong,
    ohe_weight_medium,
    both_bonus,
    tfidf_strong_threshold,
    tfidf_medium_threshold,
    ohe_only_penalty,
):
    tfidf_df = _normalize_scores(tfidf_df, "tfidf_score", "tfidf_score_norm")
    ohe_df = _normalize_scores(ohe_df, "ohe_score", "ohe_score_norm")

    final_df = pd.merge(
        tfidf_df,
        ohe_df,
        on=["userID", "recommended_movieID", "recommended_title"],
        how="outer"
    )

    if final_df.empty:
        return _empty_confidence_frame()

    final_df["tfidf_score"] = final_df["tfidf_score"].fillna(0.0)
    final_df["ohe_score"] = final_df["ohe_score"].fillna(0.0)
    final_df["tfidf_score_norm"] = final_df.get("tfidf_score_norm", 0.0)
    final_df["ohe_score_norm"] = final_df.get("ohe_score_norm", 0.0)
    final_df["tfidf_score_norm"] = final_df["tfidf_score_norm"].fillna(0.0)
    final_df["ohe_score_norm"] = final_df["ohe_score_norm"].fillna(0.0)

    final_df["has_tfidf"] = final_df["tfidf_score"] > 0
    final_df["has_ohe"] = final_df["ohe_score"] > 0
    final_df["recommended_by_both"] = (
        final_df["has_tfidf"] & final_df["has_ohe"]
    ).astype(int)

    def assign_confidence_bucket(row):
        if row["has_tfidf"] and row["tfidf_score_norm"] >= tfidf_strong_threshold:
            return "high_tfidf_confidence"
        if row["has_tfidf"] and row["tfidf_score_norm"] >= tfidf_medium_threshold:
            return "medium_tfidf_confidence"
        if (not row["has_tfidf"]) and row["has_ohe"]:
            return "ohe_fallback"
        if row["has_tfidf"] and row["has_ohe"]:
            return "low_mixed_confidence"
        if row["has_tfidf"]:
            return "tfidf_only_low_confidence"
        return "low_confidence"

    final_df["confidence_bucket"] = final_df.apply(assign_confidence_bucket, axis=1)

    def compute_final_score(row):
        tfidf_score = row["tfidf_score_norm"]
        ohe_score = row["ohe_score_norm"]
        by_both = row["recommended_by_both"]

        if row["confidence_bucket"] == "high_tfidf_confidence":
            score = (tfidf_weight_strong * tfidf_score) + (ohe_weight_strong * ohe_score)
        elif row["confidence_bucket"] == "medium_tfidf_confidence":
            score = (tfidf_weight_medium * tfidf_score) + (ohe_weight_medium * ohe_score)
        elif row["confidence_bucket"] == "ohe_fallback":
            score = ohe_score * ohe_only_penalty
        elif row["confidence_bucket"] == "low_mixed_confidence":
            score = 0.50 * tfidf_score + 0.50 * ohe_score
        elif row["confidence_bucket"] == "tfidf_only_low_confidence":
            score = 0.75 * tfidf_score
        else:
            score = max(tfidf_score, ohe_score) * 0.50

        if by_both == 1:
            score += both_bonus

        return score

    final_df["final_score"] = final_df.apply(compute_final_score, axis=1)

    def model_source(row):
        if row["has_tfidf"] and row["has_ohe"]:
            return "both_models"
        if row["has_tfidf"]:
            return "tfidf_only"
        if row["has_ohe"]:
            return "ohe_only"
        return "unknown"

    final_df["model_source"] = final_df.apply(model_source, axis=1)

    def confidence_label(row):
        if row["confidence_bucket"] == "high_tfidf_confidence":
            return "High"
        if row["confidence_bucket"] in ["medium_tfidf_confidence", "low_mixed_confidence"]:
            return "Medium"
        if row["confidence_bucket"] == "ohe_fallback":
            return "Fallback"
        return "Low"

    final_df["confidence_label"] = final_df.apply(confidence_label, axis=1)

    final_df = final_df.sort_values(
        by=["final_score", "recommended_by_both", "tfidf_score", "ohe_score", "recommended_title"],
        ascending=[False, False, False, False, True]
    ).reset_index(drop=True)

    final_df["final_rank"] = final_df.index + 1

    final_df = final_df[
        [
            "final_rank",
            "userID",
            "recommended_movieID",
            "recommended_title",
            "tfidf_score",
            "ohe_score",
            "tfidf_score_norm",
            "ohe_score_norm",
            "recommended_by_both",
            "model_source",
            "confidence_bucket",
            "confidence_label",
            "final_score",
        ]
    ]

    return final_df.head(top_n)


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


def build_confidence_router_table(
    tfidf_df,
    ohe_df,
    top_n_per_user,
    tfidf_weight_strong,
    tfidf_weight_medium,
    ohe_weight_strong,
    ohe_weight_medium,
    both_bonus,
    tfidf_strong_threshold,
    tfidf_medium_threshold,
    ohe_only_penalty,
):
    user_ids = sorted(set(tfidf_df["userID"]).union(set(ohe_df["userID"])))
    all_user_frames = []

    for user_id in user_ids:
        user_tfidf = tfidf_df[tfidf_df["userID"] == user_id].copy()
        user_ohe = ohe_df[ohe_df["userID"] == user_id].copy()

        user_conf = build_confidence_routed_for_user(
            tfidf_df=user_tfidf,
            ohe_df=user_ohe,
            top_n=top_n_per_user,
            tfidf_weight_strong=tfidf_weight_strong,
            tfidf_weight_medium=tfidf_weight_medium,
            ohe_weight_strong=ohe_weight_strong,
            ohe_weight_medium=ohe_weight_medium,
            both_bonus=both_bonus,
            tfidf_strong_threshold=tfidf_strong_threshold,
            tfidf_medium_threshold=tfidf_medium_threshold,
            ohe_only_penalty=ohe_only_penalty,
        )

        if not user_conf.empty:
            all_user_frames.append(user_conf)

    if not all_user_frames:
        return _empty_confidence_frame()

    return pd.concat(all_user_frames, ignore_index=True)


def save_confidence_table(conn, rec_df):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS user_confidence_hybrid_recommendations_top20;")
    cur.execute(
        """
        CREATE TABLE user_confidence_hybrid_recommendations_top20 (
            final_rank INTEGER NOT NULL,
            userID INTEGER NOT NULL,
            recommended_movieID INTEGER NOT NULL,
            recommended_title TEXT,
            tfidf_score REAL NOT NULL,
            ohe_score REAL NOT NULL,
            tfidf_score_norm REAL NOT NULL,
            ohe_score_norm REAL NOT NULL,
            recommended_by_both INTEGER NOT NULL,
            model_source TEXT NOT NULL,
            confidence_bucket TEXT NOT NULL,
            confidence_label TEXT NOT NULL,
            final_score REAL NOT NULL,
            PRIMARY KEY (userID, final_rank)
        );
        """
    )
    conn.commit()

    rec_df.to_sql(
        "user_confidence_hybrid_recommendations_top20",
        conn,
        if_exists="append",
        index=False,
    )

    cur.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_user_conf_hybrid_user
            ON user_confidence_hybrid_recommendations_top20(userID);

        CREATE INDEX IF NOT EXISTS idx_user_conf_hybrid_movie
            ON user_confidence_hybrid_recommendations_top20(recommended_movieID);

        CREATE INDEX IF NOT EXISTS idx_user_conf_hybrid_score
            ON user_confidence_hybrid_recommendations_top20(final_score DESC);
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
        FROM user_confidence_hybrid_recommendations_top20;
        """,
        conn,
    )

    per_user_counts = pd.read_sql_query(
        f"""
        SELECT
            userID,
            COUNT(*) AS recommendation_count
        FROM user_confidence_hybrid_recommendations_top20
        GROUP BY userID
        HAVING COUNT(*) <> {top_n_per_user}
        ORDER BY userID
        LIMIT 50;
        """,
        conn,
    )

    bucket_mix = pd.read_sql_query(
        """
        SELECT
            confidence_bucket,
            COUNT(*) AS row_count
        FROM user_confidence_hybrid_recommendations_top20
        GROUP BY confidence_bucket
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
            ROUND(tfidf_score_norm, 4) AS tfidf_score_norm,
            ROUND(ohe_score_norm, 4) AS ohe_score_norm,
            recommended_by_both,
            confidence_label,
            ROUND(final_score, 4) AS final_score,
            final_rank
        FROM user_confidence_hybrid_recommendations_top20
        WHERE userID = 1
        ORDER BY final_rank
        LIMIT 10;
        """,
        conn,
    )

    return summary, per_user_counts, bucket_mix, sample


def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING CONFIDENCE-BASED HYBRID ROUTER BUILD")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Top-N recommendations per user: {TOP_N_PER_USER}")
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
        print()

        print("[STEP 4/5] Building confidence-routed recommendations...")
        rec_df = build_confidence_router_table(
            tfidf_df=tfidf_df,
            ohe_df=ohe_df,
            top_n_per_user=TOP_N_PER_USER,
            tfidf_weight_strong=TFIDF_WEIGHT_STRONG,
            tfidf_weight_medium=TFIDF_WEIGHT_MEDIUM,
            ohe_weight_strong=OHE_WEIGHT_STRONG,
            ohe_weight_medium=OHE_WEIGHT_MEDIUM,
            both_bonus=BOTH_BONUS,
            tfidf_strong_threshold=TFIDF_STRONG_THRESHOLD,
            tfidf_medium_threshold=TFIDF_MEDIUM_THRESHOLD,
            ohe_only_penalty=OHE_ONLY_PENALTY,
        )
        print(f"Confidence-routed rows generated: {len(rec_df):,}")
        print()

        print("[STEP 5/5] Saving output table and validating results...")
        save_confidence_table(conn, rec_df)
        summary, per_user_counts, bucket_mix, sample = run_validation_queries(
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

        print("Confidence bucket mix:")
        print(bucket_mix.to_string(index=False))
        print()

        print("Sample confidence-routed recommendations for userID = 1:")
        if sample.empty:
            print("No sample rows found for userID = 1.")
        else:
            print(sample.to_string(index=False))
        print()

        end_time = datetime.now()
        duration = end_time - start_time

        print_divider()
        print("CONFIDENCE-BASED HYBRID ROUTER BUILD COMPLETED SUCCESSFULLY")
        print_divider()
        print("Created table: user_confidence_hybrid_recommendations_top20")
        print(f"Run finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total runtime: {duration}")
        print_divider()

    except Exception as e:
        print_divider("!")
        print("CONFIDENCE-BASED HYBRID ROUTER BUILD FAILED")
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
