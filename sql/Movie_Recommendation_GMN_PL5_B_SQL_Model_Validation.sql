/* ============================================================
   MODEL VALIDATION
   ------------------------------------------------------------
   Validate the simplified comparison tables and core outputs.
   ============================================================ */

SELECT 'user_content_recommendations_top20' AS table_name, COUNT(*) AS row_count
FROM user_content_recommendations_top20
UNION ALL
SELECT 'user_collaborative_knn_recommendations_top20', COUNT(*)
FROM user_collaborative_knn_recommendations_top20
UNION ALL
SELECT 'user_hybrid_recommendations_top20', COUNT(*)
FROM user_hybrid_recommendations_top20
UNION ALL
SELECT 'user_model_overlap_detail', COUNT(*)
FROM user_model_overlap_detail
UNION ALL
SELECT 'user_model_overlap_summary', COUNT(*)
FROM user_model_overlap_summary;

SELECT
    userID,
    COUNT(*) AS content_count
FROM user_content_recommendations_top20
GROUP BY userID
HAVING COUNT(*) <> 20;

SELECT
    userID,
    COUNT(*) AS collaborative_count
FROM user_collaborative_knn_recommendations_top20
GROUP BY userID
HAVING COUNT(*) <> 20;

SELECT
    userID,
    COUNT(*) AS hybrid_count
FROM user_hybrid_recommendations_top20
GROUP BY userID
HAVING COUNT(*) <> 20;

SELECT
    userID,
    COUNT(*) AS overlap_rows
FROM user_model_overlap_detail
GROUP BY userID, overlap_movieID
HAVING COUNT(*) > 1;

SELECT *
FROM user_model_overlap_summary
WHERE overlap_count > content_recommendation_count
   OR overlap_count > collaborative_recommendation_count;

SELECT *
FROM user_model_overlap_summary
ORDER BY overlap_count DESC, userID
LIMIT 25;

SELECT *
FROM user_model_overlap_summary
ORDER BY overlap_count ASC, userID
LIMIT 25;


/* ============================================================
   USER ACTIVITY SEGMENTATION
   ------------------------------------------------------------
   These checks separate:
   - top 50 most active users
   - bottom 50 least active users
   - users who need fallback because no recommendation rows exist
   ============================================================ */

WITH user_activity AS (
    SELECT
        userID,
        COUNT(*) AS interaction_count
    FROM user_movie_interactions
    GROUP BY userID
)
SELECT
    ROW_NUMBER() OVER (ORDER BY interaction_count DESC, userID) AS activity_rank,
    userID,
    interaction_count
FROM user_activity
ORDER BY activity_rank
LIMIT 50;

WITH user_activity AS (
    SELECT
        userID,
        COUNT(*) AS interaction_count
    FROM user_movie_interactions
    GROUP BY userID
)
SELECT
    ROW_NUMBER() OVER (ORDER BY interaction_count ASC, userID) AS inactivity_rank,
    userID,
    interaction_count
FROM user_activity
ORDER BY inactivity_rank
LIMIT 50;

WITH user_activity AS (
    SELECT
        userID,
        COUNT(*) AS interaction_count
    FROM user_movie_interactions
    GROUP BY userID
),
users_without_recs AS (
    SELECT
        ua.userID,
        ua.interaction_count
    FROM user_activity ua
    LEFT JOIN user_content_recommendations_top20 c
        ON ua.userID = c.userID
    LEFT JOIN user_collaborative_knn_recommendations_top20 k
        ON ua.userID = k.userID
    LEFT JOIN user_hybrid_recommendations_top20 h
        ON ua.userID = h.userID
    WHERE c.userID IS NULL
      AND k.userID IS NULL
      AND h.userID IS NULL
)
SELECT
    ROW_NUMBER() OVER (ORDER BY interaction_count ASC, userID) AS fallback_rank,
    userID,
    interaction_count
FROM users_without_recs
ORDER BY fallback_rank
LIMIT 50;


/* ============================================================
   SPECIAL CASE DIAGNOSTIC: USER 442
   ------------------------------------------------------------
   Inspect why a user with interactions can still have zero rows
   in all generated recommendation outputs.
   ============================================================ */

WITH user_activity AS (
    SELECT
        userID,
        COUNT(*) AS interaction_count,
        COUNT(DISTINCT movieID) AS distinct_movie_count,
        ROUND(AVG(rating_value), 3) AS avg_rating_value,
        MIN(rating_value) AS min_rating_value,
        MAX(rating_value) AS max_rating_value,
        SUM(CASE WHEN has_rating = 1 THEN 1 ELSE 0 END) AS rating_rows,
        SUM(CASE WHEN has_tag = 1 THEN 1 ELSE 0 END) AS tag_rows
    FROM user_movie_interactions
    WHERE userID = 442
    GROUP BY userID
)
SELECT
    ua.userID,
    ua.interaction_count,
    ua.distinct_movie_count,
    ua.avg_rating_value,
    ua.min_rating_value,
    ua.max_rating_value,
    ua.rating_rows,
    ua.tag_rows,
    CASE WHEN c.userID IS NULL THEN 0 ELSE 1 END AS has_content_recommendations,
    CASE WHEN k.userID IS NULL THEN 0 ELSE 1 END AS has_collaborative_recommendations,
    CASE WHEN h.userID IS NULL THEN 0 ELSE 1 END AS has_hybrid_recommendations
FROM user_activity ua
LEFT JOIN (
    SELECT DISTINCT userID
    FROM user_content_recommendations_top20
) c
    ON ua.userID = c.userID
LEFT JOIN (
    SELECT DISTINCT userID
    FROM user_collaborative_knn_recommendations_top20
) k
    ON ua.userID = k.userID
LEFT JOIN (
    SELECT DISTINCT userID
    FROM user_hybrid_recommendations_top20
) h
    ON ua.userID = h.userID;
