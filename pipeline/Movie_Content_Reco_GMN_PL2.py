
"""
========================================================================
CONTENT-BASED RECOMMENDER BUILD SCRIPT
========================================================================
Purpose:
    This script reads the cleaned movie feature layer from SQLite,
    builds a TF-IDF based content similarity model, and writes the
    Top-20 most similar movies for every movie back into the database.

What this script creates:
    Table: movie_content_similarity_top20

What this table contains:
    - base_movieID       : the source movie
    - base_title         : the source movie title
    - similar_movieID    : a recommended similar movie
    - similar_title      : the recommended movie title
    - similarity_score   : cosine similarity score
    - similarity_rank    : rank from 1 to 20 for each base movie

Why this is useful:
    This is the foundation for a content-based recommender system.
    Later, you can use this table to:
        1. Recommend similar movies for any movie
        2. Build user-level recommendations
        3. Validate whether your cleaning and feature engineering worked

Before running:
    Make sure your master SQL build has already created:
        - movie_content_clean
        - vw_movie_content_features

Python packages needed:
    - pandas
    - scikit-learn
========================================================================
"""

import sqlite3
import traceback
from datetime import datetime

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# ---------------------------------------------------------------------
# USER SETTINGS
# ---------------------------------------------------------------------
# Update TOP_N if you want more or fewer similar movies per movie.
# For your current design, 20 is a strong default.
# ---------------------------------------------------------------------
DB_PATH = r"G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db"
TOP_N = 20


# ---------------------------------------------------------------------
# HELPER FUNCTION: PRINT DIVIDER
# Why this exists:
#   Makes console output easier to read for new users.
# ---------------------------------------------------------------------
def print_divider(char="=", width=72):
    print(char * width)


# ---------------------------------------------------------------------
# HELPER FUNCTION: FIND THE CORRECT SOURCE OBJECT
# Why this exists:
#   combined_text should normally live in vw_movie_content_features.
#   This function checks for that first.
#   If not found, it tries movie_content_clean as a backup.
# ---------------------------------------------------------------------
def get_source_table_or_view(conn):
    checks = [
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
        "Expected vw_movie_content_features or movie_content_clean."
    )


# ---------------------------------------------------------------------
# HELPER FUNCTION: LOAD MOVIE FEATURES
# Why this exists:
#   Pulls one clean row per movie to use for TF-IDF modeling.
#   combined_text acts as the content fingerprint of each movie.
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# HELPER FUNCTION: BUILD SIMILARITY RESULTS
# Why this exists:
#   Converts combined_text into TF-IDF vectors, computes cosine similarity,
#   and keeps only the Top-N similar movies for each movie.
# ---------------------------------------------------------------------
def build_similarity_rows(movies_df, top_n=20):
    # TF-IDF settings:
    # - stop_words='english' removes very common English words
    # - ngram_range=(1, 2) uses both single words and two-word phrases
    # - min_df=1 keeps all words that appear at least once
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1
    )

    tfidf_matrix = vectorizer.fit_transform(movies_df["combined_text"].fillna(""))
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

    rows = []
    movie_ids = movies_df["movieID"].tolist()
    titles = movies_df["title"].tolist()

    for i, base_movie_id in enumerate(movie_ids):
        # Similarity to all other movies
        scores = list(enumerate(cosine_sim[i]))

        # Sort highest similarity first
        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        # Remove self-match and keep only top_n neighbors
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


# ---------------------------------------------------------------------
# HELPER FUNCTION: SAVE RESULTS TO SQLITE
# Why this exists:
#   Writes the recommender output into a permanent SQLite table so the
#   results can be queried directly in SQL later.
# ---------------------------------------------------------------------
def save_similarity_table(conn, sim_df):
    cur = conn.cursor()

    # Drop old version so each run gives a fresh rebuild
    cur.execute("DROP TABLE IF EXISTS movie_content_similarity_top20;")

    # Create final table
    cur.execute("""
        CREATE TABLE movie_content_similarity_top20 (
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

    # Insert results
    sim_df.to_sql("movie_content_similarity_top20", conn, if_exists="append", index=False)

    # Helpful indexes for faster querying later
    cur.executescript("""
        CREATE INDEX IF NOT EXISTS idx_similarity_base_movie
            ON movie_content_similarity_top20(base_movieID);

        CREATE INDEX IF NOT EXISTS idx_similarity_similar_movie
            ON movie_content_similarity_top20(similar_movieID);

        CREATE INDEX IF NOT EXISTS idx_similarity_score
            ON movie_content_similarity_top20(similarity_score DESC);
    """)
    conn.commit()


# ---------------------------------------------------------------------
# HELPER FUNCTION: RUN VALIDATION CHECKS
# Why this exists:
#   Gives fast sanity checks so the user can confirm the build worked.
# ---------------------------------------------------------------------
def run_validation_queries(conn):
    summary = pd.read_sql_query("""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT base_movieID) AS distinct_base_movies,
            MIN(similarity_rank) AS min_rank,
            MAX(similarity_rank) AS max_rank
        FROM movie_content_similarity_top20;
    """, conn)

    exceptions = pd.read_sql_query(f"""
        SELECT
            base_movieID,
            base_title,
            COUNT(*) AS recommendation_count
        FROM movie_content_similarity_top20
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
        FROM movie_content_similarity_top20
        WHERE base_movieID = 1
        ORDER BY similarity_rank
        LIMIT 10;
    """, conn)

    return summary, exceptions, sample


# ---------------------------------------------------------------------
# MAIN FUNCTION
# Why this exists:
#   Orchestrates the whole build process from load -> model -> save ->
#   validate -> success message.
# ---------------------------------------------------------------------
def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING CONTENT-BASED RECOMMENDER BUILD")
    print_divider()
    print(f"Database path: {DB_PATH}")
    print(f"Top-N similar movies per movie: {TOP_N}")
    print(f"Run started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = None

    try:
        # -------------------------------------------------------------
        # STEP 1: Connect to SQLite database
        # -------------------------------------------------------------
        print("[STEP 1/5] Connecting to SQLite database...")
        conn = sqlite3.connect(DB_PATH)
        print("Success: Database connection established.")
        print()

        # -------------------------------------------------------------
        # STEP 2: Load the movie features
        # -------------------------------------------------------------
        print("[STEP 2/5] Loading cleaned movie features...")
        movies_df, source_name = load_movie_features(conn)
        print(f"Success: Source object found -> {source_name}")
        print(f"Movies loaded for modeling: {len(movies_df):,}")

        if movies_df.empty:
            raise ValueError("No usable movies found with non-empty combined_text.")

        print("Preview of model input:")
        print(movies_df.head(5).to_string(index=False))
        print()

        # -------------------------------------------------------------
        # STEP 3: Build TF-IDF similarity model
        # -------------------------------------------------------------
        print("[STEP 3/5] Building TF-IDF vectors and cosine similarity...")
        sim_df = build_similarity_rows(movies_df, TOP_N)
        print("Success: Similarity computation completed.")
        print(f"Similarity rows generated: {len(sim_df):,}")
        print()

        # -------------------------------------------------------------
        # STEP 4: Save results back into SQLite
        # -------------------------------------------------------------
        print("[STEP 4/5] Writing results to SQLite table movie_content_similarity_top20...")
        save_similarity_table(conn, sim_df)
        print("Success: Similarity table created and indexed.")
        print()

        # -------------------------------------------------------------
        # STEP 5: Run sanity checks
        # -------------------------------------------------------------
        print("[STEP 5/5] Running validation checks...")
        summary, exceptions, sample = run_validation_queries(conn)

        print("Validation summary:")
        print(summary.to_string(index=False))
        print()

        if exceptions.empty:
            print(f"Success: Every base movie has exactly {TOP_N} recommendations.")
        else:
            print("Warning: Some movies do not have the expected recommendation count.")
            print(exceptions.head(20).to_string(index=False))
        print()

        print("Sample recommendations for base_movieID = 1:")
        if sample.empty:
            print("No sample rows found for movieID = 1.")
        else:
            print(sample.to_string(index=False))
        print()

        # -------------------------------------------------------------
        # FINAL SUCCESS MESSAGE
        # -------------------------------------------------------------
        end_time = datetime.now()
        duration = end_time - start_time

        print_divider()
        print("BUILD COMPLETED SUCCESSFULLY")
        print_divider()
        print("What this script has done:")
        print(f"1. Connected to your SQLite database at:")
        print(f"   {DB_PATH}")
        print("2. Read the cleaned content features from:")
        print(f"   {source_name}")
        print("3. Used combined_text to build a TF-IDF based content model")
        print("4. Calculated cosine similarity between every movie pair")
        print(f"5. Kept the Top {TOP_N} most similar movies for each movie")
        print("6. Created the SQLite output table:")
        print("   movie_content_similarity_top20")
        print("7. Added indexes so future SQL queries run faster")
        print("8. Ran validation checks to confirm the build completed correctly")
        print()
        print("What can we do next:")
        print(" - Query top similar movies for a movieID")
        print(" - Check whether recommendations look sensible for known movies : User expertise")
        print(" - Build user-level content recommendations from this table later- Run the second python code after validating the SQL tables")
        print()
        print(f"Run finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total runtime: {duration}")
        print_divider()

    except Exception as e:
        print_divider("!")
        print("BUILD FAILED")
        print_divider("!")
        print("Error details:")
        print(str(e))
        print()
        print("Full traceback for debugging:")
        print(traceback.format_exc())
        print()
        print("Most likely things to check:")
        print(" - Is the database path correct?")
        print(" - Did the master SQL script run successfully?")
        print(" - Does vw_movie_content_features exist?")
        print(" - Does it contain non-empty combined_text values?")
        print(" - Are pandas and scikit-learn installed?")
        print_divider("!")
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
