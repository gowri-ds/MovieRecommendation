/* ============================================================
   MODEL COMPARISON
   ------------------------------------------------------------
   Compare the simplified recommendation pipeline:
   - enriched content model
   - collaborative model
   - hybrid router
   ============================================================ */

DROP TABLE IF EXISTS user_model_overlap_detail;
DROP TABLE IF EXISTS user_model_overlap_summary;

CREATE TABLE user_model_overlap_detail AS
SELECT
    c.userID,
    c.recommended_movieID AS overlap_movieID,
    c.recommended_title AS overlap_title,
    c.recommendation_score AS content_recommendation_score,
    k.recommendation_score AS collaborative_recommendation_score,
    h.final_score AS hybrid_final_score
FROM user_content_recommendations_top20 c
INNER JOIN user_collaborative_knn_recommendations_top20 k
    ON c.userID = k.userID
   AND c.recommended_movieID = k.recommended_movieID
LEFT JOIN user_hybrid_recommendations_top20 h
    ON c.userID = h.userID
   AND c.recommended_movieID = h.recommended_movieID;

CREATE TABLE user_model_overlap_summary AS
WITH
content_counts AS (
    SELECT userID, COUNT(*) AS content_recommendation_count
    FROM user_content_recommendations_top20
    GROUP BY userID
),
collab_counts AS (
    SELECT userID, COUNT(*) AS collaborative_recommendation_count
    FROM user_collaborative_knn_recommendations_top20
    GROUP BY userID
),
hybrid_counts AS (
    SELECT userID, COUNT(*) AS hybrid_recommendation_count
    FROM user_hybrid_recommendations_top20
    GROUP BY userID
),
overlap_counts AS (
    SELECT userID, COUNT(*) AS overlap_count
    FROM user_model_overlap_detail
    GROUP BY userID
)
SELECT
    c.userID,
    c.content_recommendation_count,
    k.collaborative_recommendation_count,
    COALESCE(h.hybrid_recommendation_count, 0) AS hybrid_recommendation_count,
    COALESCE(o.overlap_count, 0) AS overlap_count,
    ROUND(
        100.0 * COALESCE(o.overlap_count, 0) / NULLIF(c.content_recommendation_count, 0),
        2
    ) AS overlap_pct_of_content,
    ROUND(
        100.0 * COALESCE(o.overlap_count, 0) / NULLIF(k.collaborative_recommendation_count, 0),
        2
    ) AS overlap_pct_of_collaborative
FROM content_counts c
INNER JOIN collab_counts k
    ON c.userID = k.userID
LEFT JOIN hybrid_counts h
    ON c.userID = h.userID
LEFT JOIN overlap_counts o
    ON c.userID = o.userID;

CREATE INDEX IF NOT EXISTS idx_user_overlap_detail_user
ON user_model_overlap_detail(userID);

CREATE INDEX IF NOT EXISTS idx_user_overlap_detail_movie
ON user_model_overlap_detail(overlap_movieID);

CREATE INDEX IF NOT EXISTS idx_user_overlap_summary_user
ON user_model_overlap_summary(userID);
