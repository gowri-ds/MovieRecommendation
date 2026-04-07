/* ============================================================
   MASTER SHEET A
   CREATE STORED COMPARISON TABLES FOR MOVIE + USER MODELS
   ------------------------------------------------------------
   PURPOSE:
   This script creates permanent stored comparison tables so that
   overlap analysis does not need to be recomputed every time.

   TABLES CREATED:
   1. movie_model_overlap_detail
   2. movie_model_overlap_summary
   3. user_model_overlap_detail
   4. user_model_overlap_summary

   MODEL PAIRS:
   - TF-IDF model vs Genre OHE model
   - Movie-level comparison
   - User-level comparison

   ASSUMPTIONS:
   - SQLite database
   - Existing model tables are already populated
   ============================================================ */


/* ============================================================
   SECTION 0 — CLEAN DROP OF OLD COMPARISON TABLES
   ------------------------------------------------------------
   Drop old copies so the script can be rerun cleanly.
   ============================================================ */

DROP TABLE IF EXISTS movie_model_overlap_detail;
DROP TABLE IF EXISTS movie_model_overlap_summary;
DROP TABLE IF EXISTS user_model_overlap_detail;
DROP TABLE IF EXISTS user_model_overlap_summary;


/* ============================================================
   SECTION 1 — MOVIE MODEL OVERLAP DETAIL
   ------------------------------------------------------------
   PURPOSE:
   Store the exact overlapping similar movies between the two
   movie-to-movie models.

   LOGIC:
   For each base movie:
   - find movies recommended by TF-IDF
   - find movies recommended by OHE
   - keep only the common similar_movieID values

   RESULT:
   One row per overlapping recommended movie for each base movie.
   ============================================================ */

CREATE TABLE movie_model_overlap_detail AS
SELECT
    tf.base_movieID,
    tf.base_title,
    tf.similar_movieID AS overlap_movieID,
    tf.similar_title AS overlap_title,

    tf.similarity_score AS tfidf_similarity_score,
    tf.similarity_rank  AS tfidf_similarity_rank,

    ohe.similarity_score AS ohe_similarity_score,
    ohe.similarity_rank  AS ohe_similarity_rank

FROM movie_content_similarity_top20 tf
INNER JOIN movie_genre_ohe_similarity_top20 ohe
    ON tf.base_movieID = ohe.base_movieID
   AND tf.similar_movieID = ohe.similar_movieID;


/* ============================================================
   SECTION 2 — MOVIE MODEL OVERLAP SUMMARY
   ------------------------------------------------------------
   PURPOSE:
   Summarize how much the two movie models agree for each base movie.

   METRICS:
   - tfidf_recommendation_count = number of TF-IDF neighbors
   - ohe_recommendation_count   = number of OHE neighbors
   - overlap_count              = number of shared neighbors
   - overlap_pct_of_tfidf       = overlap / TF-IDF count
   - overlap_pct_of_ohe         = overlap / OHE count

   EXPECTATION:
   Usually each model should have 20 rows per movie.
   If so, overlap percentage becomes overlap_count / 20 * 100.
   ============================================================ */

CREATE TABLE movie_model_overlap_summary AS
WITH
tfidf_counts AS (
    SELECT
        base_movieID,
        MAX(base_title) AS base_title,
        COUNT(*) AS tfidf_recommendation_count
    FROM movie_content_similarity_top20
    GROUP BY base_movieID
),
ohe_counts AS (
    SELECT
        base_movieID,
        MAX(base_title) AS base_title,
        COUNT(*) AS ohe_recommendation_count
    FROM movie_genre_ohe_similarity_top20
    GROUP BY base_movieID
),
overlap_counts AS (
    SELECT
        base_movieID,
        MAX(base_title) AS base_title,
        COUNT(*) AS overlap_count
    FROM movie_model_overlap_detail
    GROUP BY base_movieID
)
SELECT
    t.base_movieID,
    t.base_title,
    t.tfidf_recommendation_count,
    o.ohe_recommendation_count,
    COALESCE(ov.overlap_count, 0) AS overlap_count,

    ROUND(
        100.0 * COALESCE(ov.overlap_count, 0) / NULLIF(t.tfidf_recommendation_count, 0),
        2
    ) AS overlap_pct_of_tfidf,

    ROUND(
        100.0 * COALESCE(ov.overlap_count, 0) / NULLIF(o.ohe_recommendation_count, 0),
        2
    ) AS overlap_pct_of_ohe

FROM tfidf_counts t
INNER JOIN ohe_counts o
    ON t.base_movieID = o.base_movieID
LEFT JOIN overlap_counts ov
    ON t.base_movieID = ov.base_movieID;


/* ============================================================
   SECTION 3 — USER MODEL OVERLAP DETAIL
   ------------------------------------------------------------
   PURPOSE:
   Store the exact overlapping recommended movies between the two
   user-level recommendation models.

   LOGIC:
   For each user:
   - compare TF-IDF recommendations
   - compare OHE recommendations
   - keep movies recommended by both models

   RESULT:
   One row per overlapping recommended movie per user.
   ============================================================ */

CREATE TABLE user_model_overlap_detail AS
SELECT
    tf.userID,
    tf.recommended_movieID AS overlap_movieID,
    tf.recommended_title   AS overlap_title,

    tf.recommendation_score AS tfidf_recommendation_score,
    ohe.recommendation_score AS ohe_recommendation_score

FROM user_content_recommendations_top20 tf
INNER JOIN user_content_recommendations_genre_ohe_top20 ohe
    ON tf.userID = ohe.userID
   AND tf.recommended_movieID = ohe.recommended_movieID;


/* ============================================================
   SECTION 4 — USER MODEL OVERLAP SUMMARY
   ------------------------------------------------------------
   PURPOSE:
   Summarize how much the two user recommendation models agree
   for each user.

   METRICS:
   - tfidf_recommendation_count
   - ohe_recommendation_count
   - overlap_count
   - overlap_pct_of_tfidf
   - overlap_pct_of_ohe

   EXPECTATION:
   Usually each eligible user should have 20 recommendations.
   ============================================================ */

CREATE TABLE user_model_overlap_summary AS
WITH
tfidf_counts AS (
    SELECT
        userID,
        COUNT(*) AS tfidf_recommendation_count
    FROM user_content_recommendations_top20
    GROUP BY userID
),
ohe_counts AS (
    SELECT
        userID,
        COUNT(*) AS ohe_recommendation_count
    FROM user_content_recommendations_genre_ohe_top20
    GROUP BY userID
),
overlap_counts AS (
    SELECT
        userID,
        COUNT(*) AS overlap_count
    FROM user_model_overlap_detail
    GROUP BY userID
)
SELECT
    t.userID,
    t.tfidf_recommendation_count,
    o.ohe_recommendation_count,
    COALESCE(ov.overlap_count, 0) AS overlap_count,

    ROUND(
        100.0 * COALESCE(ov.overlap_count, 0) / NULLIF(t.tfidf_recommendation_count, 0),
        2
    ) AS overlap_pct_of_tfidf,

    ROUND(
        100.0 * COALESCE(ov.overlap_count, 0) / NULLIF(o.ohe_recommendation_count, 0),
        2
    ) AS overlap_pct_of_ohe

FROM tfidf_counts t
INNER JOIN ohe_counts o
    ON t.userID = o.userID
LEFT JOIN overlap_counts ov
    ON t.userID = ov.userID;


/* ============================================================
   SECTION 5 — INDEXES FOR PERFORMANCE
   ------------------------------------------------------------
   PURPOSE:
   Improve query speed when filtering by movie or user.
   ============================================================ */

CREATE INDEX IF NOT EXISTS idx_movie_overlap_detail_base_movie
ON movie_model_overlap_detail(base_movieID);

CREATE INDEX IF NOT EXISTS idx_movie_overlap_detail_overlap_movie
ON movie_model_overlap_detail(overlap_movieID);

CREATE INDEX IF NOT EXISTS idx_movie_overlap_summary_base_movie
ON movie_model_overlap_summary(base_movieID);

CREATE INDEX IF NOT EXISTS idx_user_overlap_detail_user
ON user_model_overlap_detail(userID);

CREATE INDEX IF NOT EXISTS idx_user_overlap_detail_movie
ON user_model_overlap_detail(overlap_movieID);

CREATE INDEX IF NOT EXISTS idx_user_overlap_summary_user
ON user_model_overlap_summary(userID);


/* ============================================================
   SECTION 6 — OPTIONAL QUICK PREVIEW
   ------------------------------------------------------------
   These are not required for table creation, but they help
   confirm that the stored tables were created successfully.
   ============================================================ */

SELECT * FROM movie_model_overlap_summary
ORDER BY overlap_count DESC, base_title
LIMIT 20;

SELECT * FROM user_model_overlap_summary
ORDER BY overlap_count DESC, userID
LIMIT 20;