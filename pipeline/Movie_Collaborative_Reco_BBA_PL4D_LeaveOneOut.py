"""
========================================================================
COLLABORATIVE KNN ITEM-ITEM LEAVE-ONE-OUT TUNING SCRIPT
========================================================================
Purpose:
    This pipeline version turns Burcu's BBA leave-one-out tuning logic
    into a reproducible evaluation step for the collaborative model.

What this script creates:
    Table: collaborative_knn_leave_one_out_user_results
    Table: collaborative_knn_leave_one_out_summary

Evaluation design:
    - For each eligible user, hold out one liked movie
    - Rebuild recommendations from the remaining liked movies
    - Check whether the held-out movie appears in the top-N list
    - Repeat for multiple K neighbor settings

Why this is useful:
    This keeps Burcu's collaborative tuning workflow inside the shared
    pipeline using the BBA file naming convention.
========================================================================
"""

import sqlite3
import traceback
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from Movie_Collaborative_Reco_BBA_PL4C import DB_PATH, LIKED_RATING_THRESHOLD, load_ratings


K_VALUES = [1, 3, 5, 7, 9, 11]
TOP_N = 5
MIN_LIKED_MOVIES = 2
RANDOM_SEED = 42


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


def build_rating_artifacts(ratings_df):
    pivot = ratings_df.pivot(index="userID", columns="movieID", values="rating").fillna(0.0)
    ratings_matrix = pivot.values

    cos_sim_matrix = cosine_similarity(ratings_matrix.T, ratings_matrix.T)
    np.fill_diagonal(cos_sim_matrix, 0.0)
    sorted_neighbors = np.argsort(cos_sim_matrix, axis=1)[:, ::-1]

    return {
        "pivot": pivot,
        "ratings_matrix": ratings_matrix,
        "cos_sim_matrix": cos_sim_matrix,
        "sorted_neighbors": sorted_neighbors,
        "movie_ids": list(pivot.columns),
        "user_ids": list(pivot.index),
    }


def evaluate_k_values(ratings_df, artifacts, k_values, top_n, min_liked_movies, random_seed):
    rng = np.random.default_rng(random_seed)

    ratings_matrix = artifacts["ratings_matrix"]
    cos_sim_matrix = artifacts["cos_sim_matrix"]
    sorted_neighbors = artifacts["sorted_neighbors"]
    movie_ids = artifacts["movie_ids"]
    user_ids = artifacts["user_ids"]

    title_lookup = (
        ratings_df[["movieID", "title"]]
        .drop_duplicates(subset=["movieID"])
        .set_index("movieID")["title"]
        .to_dict()
    )

    user_results = []

    for user_row_idx, user_id in enumerate(user_ids):
        user_ratings = ratings_matrix[user_row_idx]
        fav_movies = np.where(user_ratings >= LIKED_RATING_THRESHOLD)[0]

        if len(fav_movies) < min_liked_movies:
            continue

        holdout_movie_idx = int(rng.choice(fav_movies))
        holdout_movie_id = int(movie_ids[holdout_movie_idx])
        holdout_title = title_lookup.get(holdout_movie_id, "")

        temp_user = user_ratings.copy()
        temp_user[holdout_movie_idx] = 0.0

        visible_movies = np.where(temp_user >= LIKED_RATING_THRESHOLD)[0]
        rated_movies = set(np.where(temp_user >= 0.5)[0])

        for k_neighbors in k_values:
            movie_scores = {}

            for movie_idx in visible_movies:
                sim_scores = cos_sim_matrix[movie_idx]
                top_k_neighbors = sorted_neighbors[movie_idx][:k_neighbors]

                for neighbor_movie_idx in top_k_neighbors:
                    if neighbor_movie_idx in rated_movies:
                        continue

                    similarity = float(sim_scores[neighbor_movie_idx])
                    if similarity <= 0:
                        continue

                    rating = float(temp_user[movie_idx])
                    movie_scores[neighbor_movie_idx] = (
                        movie_scores.get(neighbor_movie_idx, 0.0) + similarity * rating
                    )

            ranked_movies = sorted(movie_scores.items(), key=lambda item: item[1], reverse=True)
            top_n_movie_indices = [movie_idx for movie_idx, _ in ranked_movies[:top_n]]

            hit = int(holdout_movie_idx in top_n_movie_indices)
            hit_rank = None
            if hit:
                hit_rank = top_n_movie_indices.index(holdout_movie_idx) + 1

            user_results.append(
                {
                    "userID": int(user_id),
                    "k_neighbors": int(k_neighbors),
                    "holdout_movieID": holdout_movie_id,
                    "holdout_title": holdout_title,
                    "hit": hit,
                    "hit_rank": hit_rank,
                }
            )

    return pd.DataFrame(user_results)


def build_summary_df(user_results_df, top_n):
    summary_df = (
        user_results_df.groupby("k_neighbors", as_index=False)
        .agg(
            eligible_users=("userID", "nunique"),
            hits=("hit", "sum"),
            hit_rate_at_n=("hit", "mean"),
        )
        .sort_values(by=["hit_rate_at_n", "hits", "k_neighbors"], ascending=[False, False, True])
        .copy()
    )

    summary_df["hit_rate_at_n"] = summary_df["hit_rate_at_n"].round(4)
    summary_df["evaluation_top_n"] = top_n
    return summary_df[
        ["k_neighbors", "evaluation_top_n", "eligible_users", "hits", "hit_rate_at_n"]
    ]


def save_evaluation_tables(conn, user_results_df, summary_df):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS collaborative_knn_leave_one_out_user_results;")
    cur.execute(
        """
        CREATE TABLE collaborative_knn_leave_one_out_user_results (
            userID INTEGER NOT NULL,
            k_neighbors INTEGER NOT NULL,
            holdout_movieID INTEGER NOT NULL,
            holdout_title TEXT,
            hit INTEGER NOT NULL,
            hit_rank INTEGER
        );
        """
    )
    conn.commit()

    user_results_df.to_sql(
        "collaborative_knn_leave_one_out_user_results",
        conn,
        if_exists="append",
        index=False,
    )

    cur.execute("DROP TABLE IF EXISTS collaborative_knn_leave_one_out_summary;")
    cur.execute(
        """
        CREATE TABLE collaborative_knn_leave_one_out_summary (
            k_neighbors INTEGER NOT NULL,
            evaluation_top_n INTEGER NOT NULL,
            eligible_users INTEGER NOT NULL,
            hits INTEGER NOT NULL,
            hit_rate_at_n REAL NOT NULL
        );
        """
    )
    conn.commit()

    summary_df.to_sql(
        "collaborative_knn_leave_one_out_summary",
        conn,
        if_exists="append",
        index=False,
    )


def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING COLLABORATIVE KNN LEAVE-ONE-OUT TUNING")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Like threshold: {LIKED_RATING_THRESHOLD}")
    print(f"Minimum liked movies per user: {MIN_LIKED_MOVIES}")
    print(f"Evaluation top-N: {TOP_N}")
    print(f"K values: {K_VALUES}")
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Run started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = None

    try:
        print("[STEP 1/6] Connecting to SQLite database...")
        conn = sqlite3.connect(DB_PATH)
        print("Success: Database connection established.\n")

        print("[STEP 2/6] Validating required source tables...")
        required_objects = ["user_movie_interactions", "movie_content_clean"]
        missing = [obj for obj in required_objects if not table_exists(conn, obj)]
        if missing:
            raise ValueError(f"Missing required source objects: {', '.join(missing)}")
        print("Success: Required tables are present.\n")

        print("[STEP 3/6] Loading source ratings...")
        ratings_df = load_ratings(conn)
        print(f"Rating rows loaded: {len(ratings_df):,}")
        print(f"Distinct users: {ratings_df['userID'].nunique():,}")
        print(f"Distinct movies: {ratings_df['movieID'].nunique():,}\n")

        print("[STEP 4/6] Building item-item similarity artifacts...")
        artifacts = build_rating_artifacts(ratings_df)
        print("Success: Similarity matrix and neighbor order built.\n")

        print("[STEP 5/6] Running leave-one-out tuning across K values...")
        user_results_df = evaluate_k_values(
            ratings_df=ratings_df,
            artifacts=artifacts,
            k_values=K_VALUES,
            top_n=TOP_N,
            min_liked_movies=MIN_LIKED_MOVIES,
            random_seed=RANDOM_SEED,
        )
        summary_df = build_summary_df(user_results_df, TOP_N)
        print("Tuning summary:")
        print(summary_df.to_string(index=False))
        print()

        best_row = summary_df.iloc[0]
        print(
            f"Best K based on hit rate@{TOP_N}: "
            f"{int(best_row['k_neighbors'])} "
            f"(hit rate {best_row['hit_rate_at_n']:.4f})"
        )
        print()

        print("[STEP 6/6] Saving tuning tables to SQLite...")
        save_evaluation_tables(conn, user_results_df, summary_df)
        print("Success: Collaborative leave-one-out tuning tables written to SQLite.\n")

        end_time = datetime.now()
        duration = end_time - start_time
        print_divider()
        print("COLLABORATIVE TUNING COMPLETED SUCCESSFULLY")
        print_divider()
        print("Created tables:")
        print(" - collaborative_knn_leave_one_out_user_results")
        print(" - collaborative_knn_leave_one_out_summary")
        print(f"Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Elapsed time: {duration}")
        print_divider()

    except Exception as exc:
        print_divider("!")
        print("COLLABORATIVE TUNING FAILED")
        print_divider("!")
        print(f"Error: {exc}")
        print()
        traceback.print_exc()
        print()
        raise
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
