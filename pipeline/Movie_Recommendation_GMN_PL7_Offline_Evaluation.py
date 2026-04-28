"""
========================================================================
OFFLINE EVALUATION SCRIPT
========================================================================
Purpose:
    Evaluate the main content model, the Collaborative KNN model,
    and the hybrid router using a leave-one-out offline test.

Evaluation design:
    - For each eligible user, hold out one liked movie
    - Build recommendations from the remaining liked movies
    - Check whether the held-out movie appears in the top-K results

What this script creates:
    Table: recommender_offline_eval_user_results
    Table: recommender_offline_eval_summary
========================================================================
"""

import math
import sqlite3
import traceback
from datetime import datetime

import pandas as pd

from config import DB_PATH
from Movie_Recommendation_GMN_PL6_A_HybridRouter import build_hybrid_for_user

LIKE_THRESHOLD = 4.0
MIN_LIKED_MOVIES = 5
TOP_K = 10
MODEL_TOP_N = 20

TFIDF_WEIGHT = 0.7
COLLAB_WEIGHT = 0.3
OVERLAP_BONUS = 0.05

COLLAB_K_NEIGHBORS = 11


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


def load_source_tables(conn):
    interactions_df = pd.read_sql_query(
        """
        SELECT
            userID,
            movieID,
            rating_value,
            last_rating_timestamp_unix
        FROM user_movie_interactions
        WHERE rating_value IS NOT NULL
        ORDER BY userID, last_rating_timestamp_unix, movieID;
        """,
        conn,
    )

    tfidf_similarity_df = pd.read_sql_query(
        """
        SELECT
            base_movieID,
            base_title,
            similar_movieID,
            similar_title,
            similarity_score,
            similarity_rank
        FROM movie_content_similarity_top20
        ORDER BY base_movieID, similarity_rank;
        """,
        conn,
    )

    movie_titles_df = pd.read_sql_query(
        """
        SELECT movieID, title
        FROM movie_content_clean
        ORDER BY movieID;
        """,
        conn,
    )

    return interactions_df, tfidf_similarity_df, movie_titles_df


def build_collaborative_artifacts(interactions_df):
    ratings_df = (
        interactions_df[["userID", "movieID", "rating_value"]]
        .rename(columns={"rating_value": "rating"})
        .copy()
    )
    pivot = ratings_df.pivot(index="userID", columns="movieID", values="rating").fillna(0.0)
    ratings_matrix = pivot.values

    # Cosine similarity over item columns, matching the collaborative tuning step.
    item_matrix = ratings_matrix.T
    item_sim = item_matrix @ item_matrix.T
    item_norms = ((item_matrix ** 2).sum(axis=1) ** 0.5)
    denom = item_norms[:, None] * item_norms[None, :]
    cos_sim_matrix = item_sim / denom
    cos_sim_matrix[~(cos_sim_matrix == cos_sim_matrix)] = 0.0
    cos_sim_matrix[denom == 0] = 0.0

    for idx in range(len(cos_sim_matrix)):
        cos_sim_matrix[idx, idx] = 0.0

    sorted_neighbors = cos_sim_matrix.argsort(axis=1)[:, ::-1]

    return {
        "pivot": pivot,
        "ratings_matrix": ratings_matrix,
        "cos_sim_matrix": cos_sim_matrix,
        "sorted_neighbors": sorted_neighbors,
        "movie_ids": list(pivot.columns),
        "user_ids": list(pivot.index),
        "user_id_to_row": {user_id: idx for idx, user_id in enumerate(pivot.index)},
        "movie_id_to_col": {movie_id: idx for idx, movie_id in enumerate(pivot.columns)},
    }


def build_collaborative_recommendations_for_user(
    user_id,
    holdout_movie_id,
    collaborative_artifacts,
    title_lookup,
    like_threshold,
    top_n,
    k_neighbors,
):
    if user_id not in collaborative_artifacts["user_id_to_row"]:
        return pd.DataFrame(
            columns=[
                "userID",
                "recommended_movieID",
                "recommended_title",
                "recommendation_score",
                "supporting_liked_movies",
                "avg_supporting_rating",
                "recommendation_rank",
                "support_movie_ids",
                "support_movie_titles",
            ]
        )

    user_row_idx = collaborative_artifacts["user_id_to_row"][user_id]
    user_ratings = collaborative_artifacts["ratings_matrix"][user_row_idx]
    temp_user = user_ratings.copy()

    holdout_col_idx = collaborative_artifacts["movie_id_to_col"].get(holdout_movie_id)
    if holdout_col_idx is not None:
        temp_user[holdout_col_idx] = 0.0

    visible_movies = [idx for idx in (temp_user >= like_threshold).nonzero()[0]]
    rated_movies = set((temp_user >= 0.5).nonzero()[0])

    movie_scores = {}

    for movie_idx in visible_movies:
        sim_scores = collaborative_artifacts["cos_sim_matrix"][movie_idx]
        top_k_neighbors = collaborative_artifacts["sorted_neighbors"][movie_idx][:k_neighbors]

        for neighbor_movie_idx in top_k_neighbors:
            if neighbor_movie_idx in rated_movies:
                continue

            similarity = float(sim_scores[neighbor_movie_idx])
            if similarity <= 0:
                continue

            candidate_movie_id = collaborative_artifacts["movie_ids"][neighbor_movie_idx]
            source_movie_id = collaborative_artifacts["movie_ids"][movie_idx]
            rating = float(temp_user[movie_idx])

            candidate_entry = movie_scores.setdefault(
                candidate_movie_id,
                {
                    "recommended_title": title_lookup.get(candidate_movie_id, ""),
                    "recommendation_score": 0.0,
                    "support_movie_ids": set(),
                    "support_movie_titles": set(),
                    "support_ratings": [],
                },
            )

            candidate_entry["recommendation_score"] += similarity * rating
            candidate_entry["support_movie_ids"].add(source_movie_id)
            candidate_entry["support_movie_titles"].add(title_lookup.get(source_movie_id, ""))
            candidate_entry["support_ratings"].append(rating)

    ranked_movies = sorted(
        movie_scores.items(),
        key=lambda item: (
            -item[1]["recommendation_score"],
            -len(item[1]["support_movie_ids"]),
            item[1]["recommended_title"],
        ),
    )[:top_n]

    rows = []
    for recommendation_rank, (candidate_movie_id, rec_info) in enumerate(ranked_movies, start=1):
        support_ratings = rec_info["support_ratings"]
        rows.append(
            {
                "userID": user_id,
                "recommended_movieID": candidate_movie_id,
                "recommended_title": rec_info["recommended_title"],
                "recommendation_score": round(rec_info["recommendation_score"], 6),
                "supporting_liked_movies": len(rec_info["support_movie_ids"]),
                "avg_supporting_rating": round(sum(support_ratings) / len(support_ratings), 4),
                "recommendation_rank": recommendation_rank,
                "support_movie_ids": ", ".join(map(str, sorted(rec_info["support_movie_ids"]))),
                "support_movie_titles": ", ".join(sorted(title for title in rec_info["support_movie_titles"] if title)),
            }
        )

    return pd.DataFrame(rows)


def select_holdout_rows(interactions_df, like_threshold, min_liked_movies):
    liked_df = interactions_df[interactions_df["rating_value"] >= like_threshold].copy()
    liked_df = liked_df.sort_values(
        by=["userID", "last_rating_timestamp_unix", "movieID"]
    ).copy()

    liked_counts = liked_df.groupby("userID").size().rename("liked_count").reset_index()
    eligible_users = liked_counts[liked_counts["liked_count"] >= min_liked_movies]["userID"]
    eligible_liked_df = liked_df[liked_df["userID"].isin(eligible_users)].copy()

    holdout_df = (
        eligible_liked_df.groupby("userID", as_index=False)
        .tail(1)
        .rename(columns={"movieID": "holdout_movieID", "rating_value": "holdout_rating"})
    )

    return eligible_liked_df, holdout_df, liked_counts


def build_user_model_recommendations(train_likes_df, seen_movie_ids, similarity_df, top_n):
    if train_likes_df.empty:
        return pd.DataFrame(
            columns=[
                "userID",
                "recommended_movieID",
                "recommended_title",
                "recommendation_score",
                "supporting_liked_movies",
                "avg_supporting_rating",
                "recommendation_rank",
                "support_movie_ids",
                "support_movie_titles",
            ]
        )

    candidate_df = train_likes_df.merge(
        similarity_df,
        left_on="movieID",
        right_on="base_movieID",
        how="inner",
    )

    candidate_df = candidate_df.rename(
        columns={
            "movieID": "liked_movieID",
            "rating_value": "liked_movie_rating",
            "similar_movieID": "recommended_movieID",
        }
    )

    candidate_df = candidate_df[
        ~candidate_df["recommended_movieID"].isin(seen_movie_ids)
    ].copy()

    if candidate_df.empty:
        return pd.DataFrame(
            columns=[
                "userID",
                "recommended_movieID",
                "recommended_title",
                "recommendation_score",
                "supporting_liked_movies",
                "avg_supporting_rating",
                "recommendation_rank",
                "support_movie_ids",
                "support_movie_titles",
            ]
        )

    grouped = (
        candidate_df.groupby(["userID", "recommended_movieID", "similar_title"], as_index=False)
        .agg(
            recommendation_score=("similarity_score", "sum"),
            supporting_liked_movies=("liked_movieID", "nunique"),
            avg_supporting_rating=("liked_movie_rating", "mean"),
            support_movie_ids=("liked_movieID", lambda x: ", ".join(map(str, sorted(pd.unique(x))))),
            support_movie_titles=("base_title", lambda x: ", ".join(sorted(pd.unique(x)))),
        )
        .rename(columns={"similar_title": "recommended_title"})
    )

    grouped = grouped.sort_values(
        by=["userID", "recommendation_score", "supporting_liked_movies", "recommended_title"],
        ascending=[True, False, False, True],
    ).copy()

    grouped["recommendation_rank"] = grouped.groupby("userID").cumcount() + 1
    grouped["recommendation_score"] = grouped["recommendation_score"].round(6)
    grouped["avg_supporting_rating"] = grouped["avg_supporting_rating"].round(4)

    return grouped.head(top_n)


def get_hit_metrics(rec_df, holdout_movie_id, top_k, rank_col):
    top_df = rec_df[rec_df[rank_col] <= top_k].copy()
    hit_row = top_df[top_df["recommended_movieID"] == holdout_movie_id]

    if hit_row.empty:
        return {
            "hit": 0,
            "hit_rank": None,
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "mrr_at_k": 0.0,
            "ndcg_at_k": 0.0,
        }

    rank = int(hit_row.iloc[0][rank_col])
    return {
        "hit": 1,
        "hit_rank": rank,
        "precision_at_k": 1.0 / top_k,
        "recall_at_k": 1.0,
        "mrr_at_k": 1.0 / rank,
            "ndcg_at_k": 1.0 / math.log2(rank + 1),
    }


def evaluate_all_models(
    interactions_df,
    eligible_liked_df,
    holdout_df,
    tfidf_similarity_df,
    movie_titles_df,
):
    title_lookup = dict(zip(movie_titles_df["movieID"], movie_titles_df["title"]))
    collaborative_artifacts = build_collaborative_artifacts(interactions_df)
    user_results = []

    all_seen_lookup = {
        user_id: set(group["movieID"].tolist())
        for user_id, group in interactions_df.groupby("userID")
    }
    eligible_likes_lookup = {
        user_id: group.copy()
        for user_id, group in eligible_liked_df.groupby("userID")
    }

    for _, holdout_row in holdout_df.iterrows():
        user_id = int(holdout_row["userID"])
        holdout_movie_id = int(holdout_row["holdout_movieID"])
        holdout_title = title_lookup.get(holdout_movie_id, "")

        train_likes_df = eligible_likes_lookup[user_id]
        train_likes_df = train_likes_df[train_likes_df["movieID"] != holdout_movie_id].copy()

        seen_movie_ids = set(all_seen_lookup[user_id])
        seen_movie_ids.discard(holdout_movie_id)

        tfidf_rec_df = build_user_model_recommendations(
            train_likes_df=train_likes_df,
            seen_movie_ids=seen_movie_ids,
            similarity_df=tfidf_similarity_df,
            top_n=MODEL_TOP_N,
        )

        collab_rec_df = build_collaborative_recommendations_for_user(
            user_id=user_id,
            holdout_movie_id=holdout_movie_id,
            collaborative_artifacts=collaborative_artifacts,
            title_lookup=title_lookup,
            like_threshold=LIKE_THRESHOLD,
            top_n=MODEL_TOP_N,
            k_neighbors=COLLAB_K_NEIGHBORS,
        )

        hybrid_rec_df = build_hybrid_for_user(
            content_df=tfidf_rec_df[[
                "userID",
                "recommended_movieID",
                "recommended_title",
                "recommendation_score",
            ]].rename(columns={"recommendation_score": "content_score"}),
            collab_df=collab_rec_df[[
                "userID",
                "recommended_movieID",
                "recommended_title",
                "recommendation_score",
            ]].rename(columns={"recommendation_score": "collaborative_score"}),
            top_n=MODEL_TOP_N,
            content_weight=TFIDF_WEIGHT,
            collab_weight=COLLAB_WEIGHT,
            overlap_bonus=OVERLAP_BONUS,
        )

        evaluations = [
            ("content_model", tfidf_rec_df, "recommendation_rank"),
            ("collaborative_knn_model", collab_rec_df, "recommendation_rank"),
            ("hybrid_router", hybrid_rec_df, "final_rank"),
        ]

        for model_name, rec_df, rank_col in evaluations:
            metrics = get_hit_metrics(rec_df, holdout_movie_id, TOP_K, rank_col)
            user_results.append(
                {
                    "userID": user_id,
                    "model_name": model_name,
                    "holdout_movieID": holdout_movie_id,
                    "holdout_title": holdout_title,
                    "hit": metrics["hit"],
                    "hit_rank": metrics["hit_rank"],
                    "precision_at_k": metrics["precision_at_k"],
                    "recall_at_k": metrics["recall_at_k"],
                    "mrr_at_k": metrics["mrr_at_k"],
                    "ndcg_at_k": metrics["ndcg_at_k"],
                }
            )

    return pd.DataFrame(user_results)


def build_summary_df(user_results_df):
    summary_df = (
        user_results_df.groupby("model_name", as_index=False)
        .agg(
            eligible_users=("userID", "nunique"),
            hits=("hit", "sum"),
            hit_rate_at_k=("hit", "mean"),
            precision_at_k=("precision_at_k", "mean"),
            recall_at_k=("recall_at_k", "mean"),
            mrr_at_k=("mrr_at_k", "mean"),
            ndcg_at_k=("ndcg_at_k", "mean"),
        )
        .sort_values(by=["hit_rate_at_k", "mrr_at_k"], ascending=[False, False])
        .copy()
    )

    summary_df["hit_rate_at_k"] = summary_df["hit_rate_at_k"].round(4)
    summary_df["precision_at_k"] = summary_df["precision_at_k"].round(4)
    summary_df["recall_at_k"] = summary_df["recall_at_k"].round(4)
    summary_df["mrr_at_k"] = summary_df["mrr_at_k"].round(4)
    summary_df["ndcg_at_k"] = summary_df["ndcg_at_k"].round(4)

    return summary_df


def save_evaluation_tables(conn, user_results_df, summary_df):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS recommender_offline_eval_user_results;")
    cur.execute(
        """
        CREATE TABLE recommender_offline_eval_user_results (
            userID INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            holdout_movieID INTEGER NOT NULL,
            holdout_title TEXT,
            hit INTEGER NOT NULL,
            hit_rank INTEGER,
            precision_at_k REAL NOT NULL,
            recall_at_k REAL NOT NULL,
            mrr_at_k REAL NOT NULL,
            ndcg_at_k REAL NOT NULL
        );
        """
    )
    conn.commit()

    user_results_df.to_sql(
        "recommender_offline_eval_user_results",
        conn,
        if_exists="append",
        index=False,
    )

    cur.execute("DROP TABLE IF EXISTS recommender_offline_eval_summary;")
    cur.execute(
        """
        CREATE TABLE recommender_offline_eval_summary (
            model_name TEXT NOT NULL,
            eligible_users INTEGER NOT NULL,
            hits INTEGER NOT NULL,
            hit_rate_at_k REAL NOT NULL,
            precision_at_k REAL NOT NULL,
            recall_at_k REAL NOT NULL,
            mrr_at_k REAL NOT NULL,
            ndcg_at_k REAL NOT NULL
        );
        """
    )
    conn.commit()

    summary_df.to_sql(
        "recommender_offline_eval_summary",
        conn,
        if_exists="append",
        index=False,
    )


def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING OFFLINE RECOMMENDER EVALUATION")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Like threshold: {LIKE_THRESHOLD}")
    print(f"Minimum liked movies per user: {MIN_LIKED_MOVIES}")
    print(f"Evaluation top-K: {TOP_K}")
    print(f"Run started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = None

    try:
        print("[STEP 1/6] Connecting to SQLite database...")
        conn = sqlite3.connect(DB_PATH)
        print("Success: Database connection established.")
        print()

        print("[STEP 2/6] Validating required source tables...")
        required_objects = [
            "user_movie_interactions",
            "movie_content_similarity_top20",
            "movie_content_clean",
        ]
        missing = [obj for obj in required_objects if not table_exists(conn, obj)]
        if missing:
            raise ValueError(f"Missing required source objects: {', '.join(missing)}")
        print("Success: Required tables are present.")
        print()

        print("[STEP 3/6] Loading source data...")
        (
            interactions_df,
            tfidf_similarity_df,
            movie_titles_df,
        ) = load_source_tables(conn)
        print(f"Interaction rows loaded: {len(interactions_df):,}")
        print(f"Content similarity rows loaded: {len(tfidf_similarity_df):,}")
        print()

        print("[STEP 4/6] Selecting holdout movies...")
        eligible_liked_df, holdout_df, liked_counts_df = select_holdout_rows(
            interactions_df,
            like_threshold=LIKE_THRESHOLD,
            min_liked_movies=MIN_LIKED_MOVIES,
        )
        print(f"Eligible liked rows: {len(eligible_liked_df):,}")
        print(f"Eligible users: {holdout_df['userID'].nunique():,}")
        print()

        print("[STEP 5/6] Evaluating models and routers...")
        user_results_df = evaluate_all_models(
            interactions_df=interactions_df,
            eligible_liked_df=eligible_liked_df,
            holdout_df=holdout_df,
            tfidf_similarity_df=tfidf_similarity_df,
            movie_titles_df=movie_titles_df,
        )
        summary_df = build_summary_df(user_results_df)
        print("Evaluation summary:")
        print(summary_df.to_string(index=False))
        print()

        print("[STEP 6/6] Saving evaluation tables...")
        save_evaluation_tables(conn, user_results_df, summary_df)
        print("Success: Evaluation tables written to SQLite.")
        print()

        end_time = datetime.now()
        duration = end_time - start_time

        print_divider()
        print("OFFLINE EVALUATION COMPLETED SUCCESSFULLY")
        print_divider()
        print("Created tables:")
        print(" - recommender_offline_eval_user_results")
        print(" - recommender_offline_eval_summary")
        print(f"Run finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total runtime: {duration}")
        print_divider()

    except Exception as e:
        print_divider("!")
        print("OFFLINE EVALUATION FAILED")
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
