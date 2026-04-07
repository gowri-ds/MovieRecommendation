/* ============================================================
   MASTER SHEET B
   VALIDATION QUERIES FOR STORED COMPARISON TABLES
   ------------------------------------------------------------
   PURPOSE:
   Validate that the stored overlap tables are complete, clean,
   and logically correct.

   TABLES VALIDATED:
   1. movie_model_overlap_detail
   2. movie_model_overlap_summary
   3. user_model_overlap_detail
   4. user_model_overlap_summary
   ============================================================ */


/* ============================================================
   SECTION 1 — BASIC ROW COUNTS
   ------------------------------------------------------------
   First check that all comparison tables contain data.
   ============================================================ */

SELECT 'movie_model_overlap_detail' AS table_name, COUNT(*) AS row_count
FROM movie_model_overlap_detail

UNION ALL

SELECT 'movie_model_overlap_summary' AS table_name, COUNT(*) AS row_count
FROM movie_model_overlap_summary

UNION ALL

SELECT 'user_model_overlap_detail' AS table_name, COUNT(*) AS row_count
FROM user_model_overlap_detail

UNION ALL

SELECT 'user_model_overlap_summary' AS table_name, COUNT(*) AS row_count
FROM user_model_overlap_summary;


/* ============================================================
   SECTION 2 — MOVIE SUMMARY COVERAGE
   ------------------------------------------------------------
   Every movie that exists in both source models should appear
   once in movie_model_overlap_summary.
   ============================================================ */

SELECT
    COUNT(DISTINCT tf.base_movieID) AS tfidf_movie_count,
    COUNT(DISTINCT ohe.base_movieID) AS ohe_movie_count,
    COUNT(DISTINCT s.base_movieID) AS summary_movie_count
FROM movie_content_similarity_top20 tf
JOIN movie_genre_ohe_similarity_top20 ohe
    ON tf.base_movieID = ohe.base_movieID
LEFT JOIN movie_model_overlap_summary s
    ON tf.base_movieID = s.base_movieID;


/* ============================================================
   SECTION 3 — USER SUMMARY COVERAGE
   ------------------------------------------------------------
   Every user that exists in both source user recommendation
   tables should appear once in user_model_overlap_summary.
   ============================================================ */

SELECT
    COUNT(DISTINCT tf.userID) AS tfidf_user_count,
    COUNT(DISTINCT ohe.userID) AS ohe_user_count,
    COUNT(DISTINCT s.userID) AS summary_user_count
FROM user_content_recommendations_top20 tf
JOIN user_content_recommendations_genre_ohe_top20 ohe
    ON tf.userID = ohe.userID
LEFT JOIN user_model_overlap_summary s
    ON tf.userID = s.userID;


/* ============================================================
   SECTION 4 — CHECK DUPLICATE MOVIE SUMMARY ROWS
   ------------------------------------------------------------
   There should be exactly one summary row per base_movieID.
   ============================================================ */

SELECT
    base_movieID,
    COUNT(*) AS row_count
FROM movie_model_overlap_summary
GROUP BY base_movieID
HAVING COUNT(*) > 1;


/* ============================================================
   SECTION 5 — CHECK DUPLICATE USER SUMMARY ROWS
   ------------------------------------------------------------
   There should be exactly one summary row per userID.
   ============================================================ */

SELECT
    userID,
    COUNT(*) AS row_count
FROM user_model_overlap_summary
GROUP BY userID
HAVING COUNT(*) > 1;


/* ============================================================
   SECTION 6 — CHECK DUPLICATE MOVIE DETAIL ROWS
   ------------------------------------------------------------
   There should not be repeated overlap pairs for the same
   base movie and overlap movie.
   ============================================================ */

SELECT
    base_movieID,
    overlap_movieID,
    COUNT(*) AS row_count
FROM movie_model_overlap_detail
GROUP BY base_movieID, overlap_movieID
HAVING COUNT(*) > 1;


/* ============================================================
   SECTION 7 — CHECK DUPLICATE USER DETAIL ROWS
   ------------------------------------------------------------
   There should not be repeated overlap pairs for the same
   user and overlap movie.
   ============================================================ */

SELECT
    userID,
    overlap_movieID,
    COUNT(*) AS row_count
FROM user_model_overlap_detail
GROUP BY userID, overlap_movieID
HAVING COUNT(*) > 1;


/* ============================================================
   SECTION 8 — CHECK FOR NULL KEYS IN MOVIE TABLES
   ============================================================ */

SELECT *
FROM movie_model_overlap_detail
WHERE base_movieID IS NULL
   OR overlap_movieID IS NULL;

SELECT *
FROM movie_model_overlap_summary
WHERE base_movieID IS NULL;


/* ============================================================
   SECTION 9 — CHECK FOR NULL KEYS IN USER TABLES
   ============================================================ */

SELECT *
FROM user_model_overlap_detail
WHERE userID IS NULL
   OR overlap_movieID IS NULL;

SELECT *
FROM user_model_overlap_summary
WHERE userID IS NULL;


/* ============================================================
   SECTION 10 — OVERLAP CANNOT EXCEED SOURCE COUNTS
   ------------------------------------------------------------
   overlap_count must always be less than or equal to both
   model recommendation counts.
   ============================================================ */

SELECT *
FROM movie_model_overlap_summary
WHERE overlap_count > tfidf_recommendation_count
   OR overlap_count > ohe_recommendation_count;

SELECT *
FROM user_model_overlap_summary
WHERE overlap_count > tfidf_recommendation_count
   OR overlap_count > ohe_recommendation_count;


/* ============================================================
   SECTION 11 — CHECK PERCENTAGE RANGE VALIDITY
   ------------------------------------------------------------
   Percentages should always be between 0 and 100.
   ============================================================ */

SELECT *
FROM movie_model_overlap_summary
WHERE overlap_pct_of_tfidf < 0
   OR overlap_pct_of_tfidf > 100
   OR overlap_pct_of_ohe < 0
   OR overlap_pct_of_ohe > 100;

SELECT *
FROM user_model_overlap_summary
WHERE overlap_pct_of_tfidf < 0
   OR overlap_pct_of_tfidf > 100
   OR overlap_pct_of_ohe < 0
   OR overlap_pct_of_ohe > 100;


/* ============================================================
   SECTION 12 — CHECK WHETHER SOURCE MODELS REALLY HAVE 20 ROWS
   ------------------------------------------------------------
   This is not validating overlap directly, but it tells you if
   source tables behaved as expected.
   ============================================================ */

SELECT
    base_movieID,
    COUNT(*) AS tfidf_count
FROM movie_content_similarity_top20
GROUP BY base_movieID
HAVING COUNT(*) <> 20;

SELECT
    base_movieID,
    COUNT(*) AS ohe_count
FROM movie_genre_ohe_similarity_top20
GROUP BY base_movieID
HAVING COUNT(*) <> 20;

SELECT
    userID,
    COUNT(*) AS tfidf_user_rec_count
FROM user_content_recommendations_top20
GROUP BY userID
HAVING COUNT(*) <> 20;

SELECT
    userID,
    COUNT(*) AS ohe_user_rec_count
FROM user_content_recommendations_genre_ohe_top20
GROUP BY userID
HAVING COUNT(*) <> 20;


/* ============================================================
   SECTION 13 — SAMPLE INSPECTION OF HIGHEST MOVIE OVERLAP
   ------------------------------------------------------------
   Useful for report writing and sanity checking.
   ============================================================ */

SELECT *
FROM movie_model_overlap_summary
ORDER BY overlap_count DESC, base_title
LIMIT 25;


/* ============================================================
   SECTION 14 — SAMPLE INSPECTION OF LOWEST MOVIE OVERLAP
   ------------------------------------------------------------
   These movies are where models disagree the most.
   ============================================================ */

SELECT *
FROM movie_model_overlap_summary
ORDER BY overlap_count ASC, base_title
LIMIT 25;


/* ============================================================
   SECTION 15 — SAMPLE INSPECTION OF HIGHEST USER OVERLAP
   ============================================================ */

SELECT *
FROM user_model_overlap_summary
ORDER BY overlap_count DESC, userID
LIMIT 25;


/* ============================================================
   SECTION 16 — SAMPLE INSPECTION OF LOWEST USER OVERLAP
   ============================================================ */

SELECT *
FROM user_model_overlap_summary
ORDER BY overlap_count ASC, userID
LIMIT 25;


/* ============================================================
   SECTION 17 — INSPECT MOVIE OVERLAP DETAILS FOR ONE MOVIE
   ------------------------------------------------------------
   Replace 1 with any base_movieID you want to inspect.
   ============================================================ */

SELECT *
FROM movie_model_overlap_detail
WHERE base_movieID = 1
ORDER BY tfidf_similarity_rank, ohe_similarity_rank;


/* ============================================================
   SECTION 18 — INSPECT USER OVERLAP DETAILS FOR ONE USER
   ------------------------------------------------------------
   Replace 1 with any userID you want to inspect.
   ============================================================ */

SELECT *
FROM user_model_overlap_detail
WHERE userID = 5
ORDER BY tfidf_recommendation_score DESC, ohe_recommendation_score DESC;