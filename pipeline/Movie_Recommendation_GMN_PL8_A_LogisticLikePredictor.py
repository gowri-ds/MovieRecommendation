"""
========================================================================
LOGISTIC LIKE PREDICTOR
========================================================================
Purpose:
    Train a logistic regression model that estimates whether a user is
    likely to positively rate a movie.

What this script creates:
    Table: user_hybrid_logistic_like_predictions_top20
    Table: logistic_like_model_summary

Why this is useful:
    - Adds a supervised prediction layer on top of the hybrid router
    - Estimates "will this user likely like this movie?"
    - Supports a probability-based interpretation for recommendation output

Important note:
    Logistic regression predicts like probability, not exact star ratings.
    A coarse rating band is derived from the probability for presentation.
========================================================================
"""

import sqlite3
import sys
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import DB_PATH

LIKE_THRESHOLD = 4.0
TEST_SIZE = 0.20
RANDOM_STATE = 42
PROBABILITY_THRESHOLD = 0.50

GENRE_COLUMNS = [
    "genre_action",
    "genre_adventure",
    "genre_animation",
    "genre_children",
    "genre_comedy",
    "genre_crime",
    "genre_documentary",
    "genre_drama",
    "genre_fantasy",
    "genre_film_noir",
    "genre_horror",
    "genre_imax",
    "genre_musical",
    "genre_mystery",
    "genre_romance",
    "genre_sci_fi",
    "genre_thriller",
    "genre_war",
    "genre_western",
    "genre_no_genres_listed",
]

FEATURE_COLUMNS = [
    "user_rating_count",
    "user_avg_rating",
    "user_like_rate",
    "movie_avg_rating",
    "movie_rating_count_log",
    "release_year",
    "genre_count",
    "genre_affinity",
]


def print_divider(char="=", width=72):
    print(char * width)


def table_exists(conn, object_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type IN ('table', 'view')
          AND name = ?;
        """,
        (object_name,),
    ).fetchone()
    return row is not None


def load_movie_features(conn):
    query = f"""
    SELECT
        movieID,
        title,
        title_clean,
        release_year,
        avg_rating AS movie_avg_rating,
        rating_count AS movie_rating_count,
        {", ".join(GENRE_COLUMNS)}
    FROM vw_movie_content_features
    ORDER BY movieID;
    """
    movie_df = pd.read_sql_query(query, conn)

    movie_df["release_year"] = pd.to_numeric(
        movie_df["release_year"], errors="coerce"
    ).fillna(movie_df["release_year"].median())
    movie_df["movie_avg_rating"] = pd.to_numeric(
        movie_df["movie_avg_rating"], errors="coerce"
    ).fillna(movie_df["movie_avg_rating"].median())
    movie_df["movie_rating_count"] = pd.to_numeric(
        movie_df["movie_rating_count"], errors="coerce"
    ).fillna(0)

    for col in GENRE_COLUMNS:
        movie_df[col] = pd.to_numeric(movie_df[col], errors="coerce").fillna(0).astype(float)

    movie_df["genre_count"] = movie_df[GENRE_COLUMNS].sum(axis=1).clip(lower=1.0)
    movie_df["movie_rating_count_log"] = np.log1p(movie_df["movie_rating_count"])

    return movie_df


def load_interactions(conn):
    return pd.read_sql_query(
        """
        SELECT
            userID,
            movieID,
            rating_value
        FROM user_movie_interactions
        WHERE rating_value IS NOT NULL
        ORDER BY userID, movieID;
        """,
        conn,
    )


def load_hybrid_candidates(conn):
    return pd.read_sql_query(
        """
        SELECT
            userID,
            recommended_movieID,
            recommended_title,
            final_score AS hybrid_final_score,
            final_rank AS hybrid_final_rank,
            model_source
        FROM user_hybrid_recommendations_top20
        ORDER BY userID, final_rank;
        """,
        conn,
    )


def build_user_profiles(interactions_df, movie_features_df):
    observed_df = interactions_df.merge(
        movie_features_df[["movieID"] + GENRE_COLUMNS],
        on="movieID",
        how="left",
    )
    observed_df["like_label"] = (observed_df["rating_value"] >= LIKE_THRESHOLD).astype(int)

    user_summary = (
        observed_df.groupby("userID")
        .agg(
            user_rating_count=("movieID", "count"),
            user_avg_rating=("rating_value", "mean"),
            user_like_rate=("like_label", "mean"),
        )
        .reset_index()
    )

    genre_exposure = observed_df.groupby("userID")[GENRE_COLUMNS].sum()
    genre_like_hits = (
        observed_df[GENRE_COLUMNS]
        .mul(observed_df["like_label"], axis=0)
        .groupby(observed_df["userID"])
        .sum()
    )

    user_genre_preferences = genre_like_hits.div(
        genre_exposure.replace(0, np.nan)
    )
    user_genre_preferences = user_genre_preferences.add_prefix("pref_").reset_index()

    user_profiles = user_summary.merge(user_genre_preferences, on="userID", how="left")
    global_like_rate = float(observed_df["like_label"].mean())

    return user_profiles, global_like_rate


def build_feature_frame(
    pair_df,
    user_profiles_df,
    movie_features_df,
    global_like_rate,
    movie_id_col,
    include_target=False,
):
    merged_df = pair_df.merge(user_profiles_df, on="userID", how="left")
    merged_df = merged_df.merge(
        movie_features_df,
        left_on=movie_id_col,
        right_on="movieID",
        how="left",
    )

    if merged_df.empty:
        return merged_df

    merged_df["user_rating_count"] = pd.to_numeric(
        merged_df["user_rating_count"], errors="coerce"
    ).fillna(0)
    merged_df["user_avg_rating"] = pd.to_numeric(
        merged_df["user_avg_rating"], errors="coerce"
    ).fillna(merged_df["user_avg_rating"].median())
    merged_df["user_like_rate"] = pd.to_numeric(
        merged_df["user_like_rate"], errors="coerce"
    ).fillna(global_like_rate)
    merged_df["movie_avg_rating"] = pd.to_numeric(
        merged_df["movie_avg_rating"], errors="coerce"
    ).fillna(merged_df["movie_avg_rating"].median())
    merged_df["movie_rating_count_log"] = pd.to_numeric(
        merged_df["movie_rating_count_log"], errors="coerce"
    ).fillna(0)
    merged_df["release_year"] = pd.to_numeric(
        merged_df["release_year"], errors="coerce"
    ).fillna(movie_features_df["release_year"].median())
    merged_df["genre_count"] = pd.to_numeric(
        merged_df["genre_count"], errors="coerce"
    ).fillna(1.0).clip(lower=1.0)

    for genre_col in GENRE_COLUMNS:
        pref_col = f"pref_{genre_col}"
        merged_df[genre_col] = pd.to_numeric(
            merged_df[genre_col], errors="coerce"
        ).fillna(0.0)
        merged_df[pref_col] = pd.to_numeric(
            merged_df[pref_col], errors="coerce"
        ).fillna(global_like_rate)

    affinity_numerator = sum(
        merged_df[f"pref_{genre_col}"] * merged_df[genre_col]
        for genre_col in GENRE_COLUMNS
    )
    merged_df["genre_affinity"] = affinity_numerator / merged_df["genre_count"]

    if include_target:
        merged_df["like_label"] = (merged_df["rating_value"] >= LIKE_THRESHOLD).astype(int)

    return merged_df


def train_logistic_like_model(training_df):
    X = training_df[FEATURE_COLUMNS].copy()
    y = training_df["like_label"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "logistic",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )
    model.fit(X_train, y_train)

    test_probability = model.predict_proba(X_test)[:, 1]
    test_prediction = (test_probability >= PROBABILITY_THRESHOLD).astype(int)

    metrics = {
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "positive_rate_train": float(y_train.mean()),
        "positive_rate_test": float(y_test.mean()),
        "accuracy": float(accuracy_score(y_test, test_prediction)),
        "precision": float(precision_score(y_test, test_prediction, zero_division=0)),
        "recall": float(recall_score(y_test, test_prediction, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, test_probability)),
    }

    return model, metrics


def probability_to_rating_band(probability):
    if probability >= 0.80:
        return "4.0_to_5.0"
    if probability >= 0.60:
        return "3.0_to_4.0"
    if probability >= 0.40:
        return "2.0_to_3.0"
    return "0.5_to_2.0"


def score_hybrid_candidates(model, candidate_df):
    if candidate_df.empty:
        return pd.DataFrame(
            columns=[
                "userID",
                "recommended_movieID",
                "recommended_title",
                "hybrid_final_rank",
                "hybrid_final_score",
                "model_source",
                "predicted_like_probability",
                "predicted_like_label",
                "predicted_rating_band",
                "probability_rank",
            ]
        )

    scored_df = candidate_df.copy()
    scored_df["predicted_like_probability"] = model.predict_proba(
        scored_df[FEATURE_COLUMNS]
    )[:, 1]
    scored_df["predicted_like_label"] = (
        scored_df["predicted_like_probability"] >= PROBABILITY_THRESHOLD
    ).astype(int)
    scored_df["predicted_rating_band"] = scored_df[
        "predicted_like_probability"
    ].apply(probability_to_rating_band)

    scored_df = scored_df.sort_values(
        by=["userID", "predicted_like_probability", "hybrid_final_score", "hybrid_final_rank"],
        ascending=[True, False, False, True],
    ).reset_index(drop=True)

    scored_df["probability_rank"] = (
        scored_df.groupby("userID").cumcount() + 1
    )

    return scored_df[
        [
            "userID",
            "recommended_movieID",
            "recommended_title",
            "hybrid_final_rank",
            "hybrid_final_score",
            "model_source",
            "predicted_like_probability",
            "predicted_like_label",
            "predicted_rating_band",
            "probability_rank",
        ]
    ]


def save_prediction_tables(conn, predictions_df, metrics, training_df, candidate_count):
    conn.execute("DROP TABLE IF EXISTS user_hybrid_logistic_like_predictions_top20;")
    conn.execute("DROP TABLE IF EXISTS logistic_like_model_summary;")
    conn.commit()

    predictions_df.to_sql(
        "user_hybrid_logistic_like_predictions_top20",
        conn,
        if_exists="replace",
        index=False,
    )

    summary_df = pd.DataFrame(
        [
            {
                "like_threshold": LIKE_THRESHOLD,
                "probability_threshold": PROBABILITY_THRESHOLD,
                "training_rows": len(training_df),
                "training_users": training_df["userID"].nunique(),
                "training_movies": training_df["movieID"].nunique(),
                "candidate_rows_scored": candidate_count,
                "train_rows": metrics["train_rows"],
                "test_rows": metrics["test_rows"],
                "positive_rate_train": round(metrics["positive_rate_train"], 4),
                "positive_rate_test": round(metrics["positive_rate_test"], 4),
                "accuracy": round(metrics["accuracy"], 4),
                "precision": round(metrics["precision"], 4),
                "recall": round(metrics["recall"], 4),
                "roc_auc": round(metrics["roc_auc"], 4),
            }
        ]
    )
    summary_df.to_sql(
        "logistic_like_model_summary",
        conn,
        if_exists="replace",
        index=False,
    )

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_user_hybrid_logistic_predictions_user
            ON user_hybrid_logistic_like_predictions_top20(userID);

        CREATE INDEX IF NOT EXISTS idx_user_hybrid_logistic_predictions_movie
            ON user_hybrid_logistic_like_predictions_top20(recommended_movieID);

        CREATE INDEX IF NOT EXISTS idx_user_hybrid_logistic_predictions_probability
            ON user_hybrid_logistic_like_predictions_top20(predicted_like_probability DESC);
        """
    )
    conn.commit()


def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING LOGISTIC LIKE PREDICTOR BUILD")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Like threshold: {LIKE_THRESHOLD}")
    print(f"Probability threshold: {PROBABILITY_THRESHOLD}")
    print(f"Run started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = None

    try:
        print("[STEP 1/6] Connecting to SQLite database...")
        conn = sqlite3.connect(DB_PATH)
        print("Success: Database connection established.")
        print()

        print("[STEP 2/6] Validating required source objects...")
        required_objects = [
            "user_movie_interactions",
            "vw_movie_content_features",
            "user_hybrid_recommendations_top20",
        ]
        missing = [obj for obj in required_objects if not table_exists(conn, obj)]
        if missing:
            raise ValueError(f"Missing required source objects: {', '.join(missing)}")
        print("Success: Required source objects are present.")
        print()

        print("[STEP 3/6] Loading movie, interaction, and candidate data...")
        movie_features_df = load_movie_features(conn)
        interactions_df = load_interactions(conn)
        hybrid_candidates_df = load_hybrid_candidates(conn)
        print(f"Movie feature rows loaded: {len(movie_features_df):,}")
        print(f"Observed user-movie interaction rows loaded: {len(interactions_df):,}")
        print(f"Hybrid candidate rows loaded: {len(hybrid_candidates_df):,}")
        print()

        print("[STEP 4/6] Building training features and fitting logistic regression...")
        user_profiles_df, global_like_rate = build_user_profiles(
            interactions_df, movie_features_df
        )
        training_feature_df = build_feature_frame(
            pair_df=interactions_df,
            user_profiles_df=user_profiles_df,
            movie_features_df=movie_features_df,
            global_like_rate=global_like_rate,
            movie_id_col="movieID",
            include_target=True,
        )

        model, metrics = train_logistic_like_model(training_feature_df)
        print(f"Training rows used: {len(training_feature_df):,}")
        print(f"Distinct users in training: {training_feature_df['userID'].nunique():,}")
        print(f"Distinct movies in training: {training_feature_df['movieID'].nunique():,}")
        print("Model metrics:")
        print(
            pd.DataFrame([metrics]).round(4).to_string(index=False)
        )
        print()

        print("[STEP 5/6] Scoring hybrid recommendation candidates...")
        hybrid_candidate_features = build_feature_frame(
            pair_df=hybrid_candidates_df.rename(
                columns={"recommended_movieID": "movieID"}
            ),
            user_profiles_df=user_profiles_df,
            movie_features_df=movie_features_df,
            global_like_rate=global_like_rate,
            movie_id_col="movieID",
            include_target=False,
        ).rename(columns={"movieID": "recommended_movieID"})

        prediction_df = score_hybrid_candidates(model, hybrid_candidate_features)
        print(f"Prediction rows created: {len(prediction_df):,}")
        print()

        print("[STEP 6/6] Saving output tables and printing sample rows...")
        save_prediction_tables(
            conn=conn,
            predictions_df=prediction_df,
            metrics=metrics,
            training_df=training_feature_df,
            candidate_count=len(prediction_df),
        )

        sample_df = pd.read_sql_query(
            """
            SELECT
                userID,
                recommended_movieID,
                recommended_title,
                hybrid_final_rank,
                ROUND(hybrid_final_score, 4) AS hybrid_final_score,
                ROUND(predicted_like_probability, 4) AS predicted_like_probability,
                predicted_like_label,
                predicted_rating_band,
                probability_rank
            FROM user_hybrid_logistic_like_predictions_top20
            WHERE userID = 1
            ORDER BY probability_rank
            LIMIT 10;
            """,
            conn,
        )

        print("Sample predictions for userID = 1:")
        if sample_df.empty:
            print("No sample prediction rows found for userID = 1.")
        else:
            print(sample_df.to_string(index=False))
        print()

        end_time = datetime.now()
        duration = end_time - start_time

        print_divider()
        print("LOGISTIC LIKE PREDICTOR COMPLETED SUCCESSFULLY")
        print_divider()
        print("Created table: user_hybrid_logistic_like_predictions_top20")
        print("Created table: logistic_like_model_summary")
        print("This model estimates the probability that a user will like a hybrid recommendation.")
        print(f"Run finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total runtime: {duration}")
        print_divider()

    except Exception as exc:
        print_divider("!")
        print("LOGISTIC LIKE PREDICTOR FAILED")
        print_divider("!")
        print("Error details:")
        print(str(exc))
        print()
        print("Full traceback for debugging:")
        print(traceback.format_exc())
        print_divider("!")
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
