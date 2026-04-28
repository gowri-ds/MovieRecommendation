"""
========================================================================
BERT CONTENT SIMILARITY BUILD SCRIPT
========================================================================
Purpose:
    Build a semantic content similarity model using sentence-transformer
    embeddings instead of TF-IDF.

What this script creates:
    Table: movie_content_similarity_bert_top20

What this table contains:
    - base_movieID       : the source movie
    - base_title         : the source movie title
    - similar_movieID    : a recommended similar movie
    - similar_title      : the recommended movie title
    - similarity_score   : cosine similarity score
    - similarity_rank    : rank from 1 to 20 for each base movie

Why this is useful:
    This gives you an experimental semantic content model that can be
    compared against the existing TF-IDF content similarity pipeline.

Before running:
    Make sure your SQL/content build has already created:
        - vw_movie_content_features_enriched (preferred)
        - vw_movie_content_features
        - movie_content_clean

Python packages needed:
    - pandas
    - numpy
    - sentence-transformers
========================================================================
"""

import sqlite3
import traceback
from datetime import datetime

import numpy as np
import pandas as pd

from config import DB_PATH

TOP_N = 20
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 64


def print_divider(char="=", width=72):
    print(char * width)


def get_source_table_or_view(conn):
    checks = [
        ("vw_movie_content_features_enriched", "combined_text"),
        ("vw_movie_content_features", "combined_text"),
        ("movie_content_clean", "combined_text"),
    ]

    cur = conn.cursor()
    for object_name, required_col in checks:
        try:
            cur.execute(f"PRAGMA table_info({object_name});")
            cols = [row[1] for row in cur.fetchall()]
            if cols and required_col in cols:
                return object_name
        except sqlite3.Error:
            pass

    raise ValueError(
        "Could not find a usable source with combined_text. "
        "Expected vw_movie_content_features_enriched, "
        "vw_movie_content_features, or movie_content_clean."
    )


def load_movie_features(conn):
    source_name = get_source_table_or_view(conn)

    query = f"""
    SELECT
        movieID,
        title,
        title_clean,
        genres_pipe,
        combined_text
    FROM {source_name}
    WHERE combined_text IS NOT NULL
      AND TRIM(combined_text) <> ''
    ORDER BY movieID;
    """

    df = pd.read_sql_query(query, conn)
    return df, source_name


def build_similarity_rows(movies_df, top_n=20, model_name=EMBEDDING_MODEL_NAME):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is not installed. "
            "Install it before running the BERT content pipeline."
        ) from exc

    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        movies_df["combined_text"].fillna("").tolist(),
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    cosine_sim = np.matmul(embeddings, embeddings.T)

    rows = []
    movie_ids = movies_df["movieID"].tolist()
    titles = movies_df["title"].tolist()

    for i, base_movie_id in enumerate(movie_ids):
        scores = list(enumerate(cosine_sim[i]))
        scores = sorted(scores, key=lambda item: item[1], reverse=True)
        top_matches = [(j, score) for j, score in scores if j != i][:top_n]

        for rank, (j, score) in enumerate(top_matches, start=1):
            rows.append(
                {
                    "base_movieID": int(base_movie_id),
                    "base_title": titles[i],
                    "similar_movieID": int(movie_ids[j]),
                    "similar_title": titles[j],
                    "similarity_score": float(score),
                    "similarity_rank": int(rank),
                }
            )

    return pd.DataFrame(rows)


def save_similarity_table(conn, sim_df):
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS movie_content_similarity_bert_top20;")
    cur.execute(
        """
        CREATE TABLE movie_content_similarity_bert_top20 (
            base_movieID INTEGER NOT NULL,
            base_title TEXT,
            similar_movieID INTEGER NOT NULL,
            similar_title TEXT,
            similarity_score REAL NOT NULL,
            similarity_rank INTEGER NOT NULL,
            PRIMARY KEY (base_movieID, similarity_rank)
        );
        """
    )
    conn.commit()

    sim_df.to_sql(
        "movie_content_similarity_bert_top20",
        conn,
        if_exists="append",
        index=False,
    )

    cur.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_similarity_bert_base_movie
            ON movie_content_similarity_bert_top20(base_movieID);

        CREATE INDEX IF NOT EXISTS idx_similarity_bert_similar_movie
            ON movie_content_similarity_bert_top20(similar_movieID);

        CREATE INDEX IF NOT EXISTS idx_similarity_bert_score
            ON movie_content_similarity_bert_top20(similarity_score DESC);
        """
    )
    conn.commit()


def run_validation_queries(conn):
    summary = pd.read_sql_query(
        """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT base_movieID) AS distinct_base_movies,
            MIN(similarity_rank) AS min_rank,
            MAX(similarity_rank) AS max_rank
        FROM movie_content_similarity_bert_top20;
        """,
        conn,
    )

    exceptions = pd.read_sql_query(
        f"""
        SELECT
            base_movieID,
            base_title,
            COUNT(*) AS recommendation_count
        FROM movie_content_similarity_bert_top20
        GROUP BY base_movieID, base_title
        HAVING COUNT(*) <> {TOP_N}
        ORDER BY base_movieID;
        """,
        conn,
    )

    sample = pd.read_sql_query(
        """
        SELECT
            base_movieID,
            base_title,
            similar_movieID,
            similar_title,
            ROUND(similarity_score, 4) AS similarity_score,
            similarity_rank
        FROM movie_content_similarity_bert_top20
        WHERE base_movieID = 1
        ORDER BY similarity_rank
        LIMIT 10;
        """,
        conn,
    )

    return summary, exceptions, sample


def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING BERT CONTENT SIMILARITY BUILD")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Top-N similar movies per base movie: {TOP_N}")
    print(f"Embedding model: {EMBEDDING_MODEL_NAME}")
    print(f"Run started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = None

    try:
        print("[STEP 1/5] Connecting to SQLite database...")
        conn = sqlite3.connect(DB_PATH)
        print("Success: Database connection established.")
        print()

        print("[STEP 2/5] Loading movie content features...")
        movies_df, source_name = load_movie_features(conn)
        if movies_df.empty:
            raise ValueError("No usable movies found with non-empty combined_text.")
        print(f"Success: Loaded {len(movies_df):,} movies from {source_name}.")
        print()

        print("[STEP 3/5] Building BERT semantic similarity matrix...")
        sim_df = build_similarity_rows(
            movies_df=movies_df,
            top_n=TOP_N,
            model_name=EMBEDDING_MODEL_NAME,
        )
        print(f"Success: Built {len(sim_df):,} similarity rows.")
        print()

        print("[STEP 4/5] Writing results to SQLite table movie_content_similarity_bert_top20...")
        save_similarity_table(conn, sim_df)
        print("Success: BERT similarity table written.")
        print()

        print("[STEP 5/5] Running validation queries...")
        summary, exceptions, sample = run_validation_queries(conn)

        print("Validation summary:")
        print(summary.to_string(index=False))
        print()

        if exceptions.empty:
            print(f"Success: Every base movie has exactly {TOP_N} recommendations.")
        else:
            print("Warning: Some base movies do not have the expected recommendation count.")
            print(exceptions.to_string(index=False))
        print()

        print("Sample similar movies for base_movieID = 1:")
        if sample.empty:
            print("No sample rows found for base_movieID = 1.")
        else:
            print(sample.to_string(index=False))
        print()

        end_time = datetime.now()
        duration = end_time - start_time

        print_divider()
        print("BERT CONTENT SIMILARITY BUILD COMPLETED SUCCESSFULLY")
        print_divider()
        print("Created table: movie_content_similarity_bert_top20")
        print("This table stores semantic movie similarity using sentence embeddings.")
        print(f"Run finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total runtime: {duration}")
        print_divider()

    except Exception as exc:
        print_divider("!")
        print("BERT CONTENT SIMILARITY BUILD FAILED")
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
