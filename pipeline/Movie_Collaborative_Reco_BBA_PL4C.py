"""
========================================================================
USER-LEVEL COLLABORATIVE KNN ITEM-ITEM RECOMMENDATION BUILD SCRIPT
========================================================================
Purpose:
    This pipeline version operationalizes Burcu's collaborative
    filtering work from the BBA scripts into a reusable build step.

What this script creates:
    Table: user_collaborative_knn_recommendations_top20

Logic:
    Step 1:
        Load user ratings from user_movie_interactions.

    Step 2:
        Build a user-item matrix and fit an item-item nearest-neighbor
        model using cosine distance.

    Step 3:
        For each user, look at movies they rated highly and gather
        candidate neighbors from similar items they have not seen.

    Step 4:
        Aggregate weighted scores and keep the Top-N recommendations.

Why this is useful:
    This makes the collaborative recommender reproducible inside the
    shared pipeline while keeping Burcu's BBA naming convention.
========================================================================
"""

import sqlite3
import traceback
from datetime import datetime

import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors

from config import DB_PATH

LIKED_RATING_THRESHOLD = 4.0
TOP_N_PER_USER = 20
K_NEIGHBORS = 9


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


def load_ratings(conn):
    query = """
    SELECT
        umi.userID,
        umi.movieID,
        umi.rating_value AS rating,
        COALESCE(mcc.title_clean, mcc.title) AS title
    FROM user_movie_interactions umi
    LEFT JOIN movie_content_clean mcc
        ON mcc.movieID = umi.movieID
    WHERE umi.rating_value IS NOT NULL
    ORDER BY umi.userID, umi.movieID;
    """
    return pd.read_sql_query(query, conn)


def build_item_neighbors(ratings_df, k_neighbors):
    pivot = ratings_df.pivot(index="userID", columns="movieID", values="rating").fillna(0.0)
    ratings_sparse = csr_matrix(pivot.values)

    item_model = NearestNeighbors(
        n_neighbors=k_neighbors + 1,
        metric="cosine",
        algorithm="brute",
    )
    item_model.fit(ratings_sparse.T)

    distances, indices = item_model.kneighbors(ratings_sparse.T)

    movie_ids = list(pivot.columns)
    movie_id_to_col = {movie_id: idx for idx, movie_id in enumerate(movie_ids)}
    col_to_movie_id = {idx: movie_id for idx, movie_id in enumerate(movie_ids)}
    user_ids = list(pivot.index)
    user_id_to_row = {user_id: idx for idx, user_id in enumerate(user_ids)}

    return {
        "pivot": pivot,
        "distances": distances,
        "indices": indices,
        "movie_id_to_col": movie_id_to_col,
        "col_to_movie_id": col_to_movie_id,
        "user_ids": user_ids,
        "user_id_to_row": user_id_to_row,
    }


def build_user_recommendations(ratings_df, model_parts, top_n_per_user):
    title_map = (
        ratings_df[["movieID", "title"]]
        .drop_duplicates(subset=["movieID"])
        .set_index("movieID")["title"]
        .to_dict()
    )

    distances = model_parts["distances"]
    indices = model_parts["indices"]
    movie_id_to_col = model_parts["movie_id_to_col"]
    col_to_movie_id = model_parts["col_to_movie_id"]
    user_id_to_row = model_parts["user_id_to_row"]

    recommendation_rows = []

    for user_id, user_group in ratings_df.groupby("userID", sort=True):
        user_row_idx = user_id_to_row[user_id]
        _ = model_parts["pivot"].iloc[user_row_idx]
        seen_movie_ids = set(user_group["movieID"])

        liked_df = (
            user_group[user_group["rating"] >= LIKED_RATING_THRESHOLD]
            .sort_values(by=["rating", "movieID"], ascending=[False, True])
            .copy()
        )

        if liked_df.empty:
            continue

        candidate_scores = {}

        for liked_row in liked_df.itertuples(index=False):
            source_movie_id = liked_row.movieID
            source_rating = float(liked_row.rating)
            source_title = liked_row.title
            source_col_idx = movie_id_to_col.get(source_movie_id)

            if source_col_idx is None:
                continue

            neighbor_indices = indices[source_col_idx]
            neighbor_distances = distances[source_col_idx]

            for neighbor_col_idx, neighbor_distance in zip(neighbor_indices[1:], neighbor_distances[1:]):
                candidate_movie_id = col_to_movie_id[neighbor_col_idx]
                if candidate_movie_id in seen_movie_ids:
                    continue

                similarity = 1.0 - float(neighbor_distance)
                if similarity <= 0:
                    continue

                candidate_entry = candidate_scores.setdefault(
                    candidate_movie_id,
                    {
                        "recommended_title": title_map.get(candidate_movie_id, ""),
                        "recommendation_score": 0.0,
                        "support_movie_ids": set(),
                        "support_movie_titles": set(),
                        "support_ratings": [],
                    },
                )

                candidate_entry["recommendation_score"] += similarity * source_rating
                candidate_entry["support_movie_ids"].add(source_movie_id)
                candidate_entry["support_movie_titles"].add(source_title)
                candidate_entry["support_ratings"].append(source_rating)

        if not candidate_scores:
            continue

        ranked_candidates = sorted(
            candidate_scores.items(),
            key=lambda item: (
                -item[1]["recommendation_score"],
                -len(item[1]["support_movie_ids"]),
                item[1]["recommended_title"] or "",
            ),
        )[:top_n_per_user]

        for recommendation_rank, (candidate_movie_id, rec_info) in enumerate(ranked_candidates, start=1):
            support_ratings = rec_info["support_ratings"]
            recommendation_rows.append(
                {
                    "userID": user_id,
                    "recommended_movieID": candidate_movie_id,
                    "recommended_title": rec_info["recommended_title"],
                    "recommendation_score": round(rec_info["recommendation_score"], 6),
                    "supporting_liked_movies": len(rec_info["support_movie_ids"]),
                    "avg_supporting_rating": round(sum(support_ratings) / len(support_ratings), 4),
                    "recommendation_rank": recommendation_rank,
                    "support_movie_ids": ", ".join(map(str, sorted(rec_info["support_movie_ids"]))),
                    "support_movie_titles": ", ".join(sorted(rec_info["support_movie_titles"])),
                }
            )

    return pd.DataFrame(
        recommendation_rows,
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
        ],
    )


def save_user_recommendation_table(conn, rec_df):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS user_collaborative_knn_recommendations_top20;")
    cur.execute(
        """
        CREATE TABLE user_collaborative_knn_recommendations_top20 (
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
        """
    )
    conn.commit()

    rec_df.to_sql(
        "user_collaborative_knn_recommendations_top20",
        conn,
        if_exists="append",
        index=False,
    )

    cur.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_user_collab_knn_recs_user
            ON user_collaborative_knn_recommendations_top20(userID);

        CREATE INDEX IF NOT EXISTS idx_user_collab_knn_recs_movie
            ON user_collaborative_knn_recommendations_top20(recommended_movieID);

        CREATE INDEX IF NOT EXISTS idx_user_collab_knn_recs_score
            ON user_collaborative_knn_recommendations_top20(recommendation_score DESC);
        """
    )
    conn.commit()


def run_validation_queries(conn, top_n_per_user):
    summary = pd.read_sql_query(
        """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT userID) AS distinct_users,
            MIN(recommendation_rank) AS min_rank,
            MAX(recommendation_rank) AS max_rank
        FROM user_collaborative_knn_recommendations_top20;
        """,
        conn,
    )

    per_user_counts = pd.read_sql_query(
        f"""
        SELECT
            userID,
            COUNT(*) AS recommendation_count
        FROM user_collaborative_knn_recommendations_top20
        GROUP BY userID
        HAVING COUNT(*) <> {top_n_per_user}
        ORDER BY userID
        LIMIT 50;
        """,
        conn,
    )

    sample = pd.read_sql_query(
        """
        SELECT
            userID,
            recommended_movieID,
            recommended_title,
            ROUND(recommendation_score, 4) AS recommendation_score,
            supporting_liked_movies,
            ROUND(avg_supporting_rating, 2) AS avg_supporting_rating,
            recommendation_rank
        FROM user_collaborative_knn_recommendations_top20
        WHERE userID = 1
        ORDER BY recommendation_rank
        LIMIT 10;
        """,
        conn,
    )

    return summary, per_user_counts, sample


def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING USER-LEVEL COLLABORATIVE KNN ITEM-ITEM BUILD")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Liked rating threshold: {LIKED_RATING_THRESHOLD}")
    print(f"Top-N recommendations per user: {TOP_N_PER_USER}")
    print(f"K neighbors per liked movie: {K_NEIGHBORS}")
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

        print("[STEP 4/6] Fitting item-item KNN model...")
        model_parts = build_item_neighbors(ratings_df, K_NEIGHBORS)
        print("Success: KNN model built.\n")

        print("[STEP 5/6] Building user-level recommendations...")
        rec_df = build_user_recommendations(
            ratings_df=ratings_df,
            model_parts=model_parts,
            top_n_per_user=TOP_N_PER_USER,
        )
        print(f"Success: Built {len(rec_df):,} recommendation rows.\n")

        print("[STEP 6/6] Writing results to SQLite...")
        save_user_recommendation_table(conn, rec_df)
        print("Success: Collaborative recommendation table created and indexed.\n")

        print_divider("-")
        print("VALIDATION")
        print_divider("-")
        summary_df, per_user_counts_df, sample_df = run_validation_queries(conn, TOP_N_PER_USER)

        print("Summary:")
        print(summary_df.to_string(index=False))
        print()

        if per_user_counts_df.empty:
            print(f"Success: Every user has exactly {TOP_N_PER_USER} recommendations.")
        else:
            print("Note: Some users have fewer than the requested Top-N recommendations.")
            print(per_user_counts_df.to_string(index=False))
        print()

        print("Sample recommendations for userID = 1:")
        if sample_df.empty:
            print("No recommendations found for userID = 1.")
        else:
            print(sample_df.to_string(index=False))
        print()

        end_time = datetime.now()
        elapsed = end_time - start_time
        print_divider()
        print("PIPELINE STEP COMPLETE")
        print_divider()
        print(f"Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Elapsed time: {elapsed}")
        print("Output table: user_collaborative_knn_recommendations_top20")
        print_divider()

    except Exception as exc:
        print_divider("!")
        print("PIPELINE FAILED")
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
