/*
========================================================================
HYBRID RECOMMENDATION SQL QUERIES
========================================================================
Purpose:
    Validate and inspect the output of the hybrid recommendation
    pipeline step.

Source table:
    user_hybrid_recommendations_top20
========================================================================
*/

/*
Query 1: Confirm the hybrid table exists
*/
SELECT name
FROM sqlite_master
WHERE type = 'table'
  AND name = 'user_hybrid_recommendations_top20';


/*
Query 2: Overall summary of the hybrid output
*/
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT userID) AS distinct_users,
    MIN(final_rank) AS min_rank,
    MAX(final_rank) AS max_rank,
    ROUND(AVG(final_score), 4) AS avg_final_score,
    ROUND(AVG(recommended_by_both), 4) AS share_recommended_by_both
FROM user_hybrid_recommendations_top20;


/*
Query 3: Top 20 hybrid recommendations for one user
Change userID as needed
*/
SELECT
    userID,
    final_rank,
    recommended_movieID,
    recommended_title,
    ROUND(content_score, 4) AS content_score,
    ROUND(collaborative_score, 4) AS collaborative_score,
    ROUND(content_score_norm, 4) AS content_score_norm,
    ROUND(collaborative_score_norm, 4) AS collaborative_score_norm,
    recommended_by_both,
    model_source,
    ROUND(final_score, 4) AS final_score
FROM user_hybrid_recommendations_top20
WHERE userID = 54
ORDER BY final_rank;


/*
Query 4: Only the movies recommended by both models
*/
SELECT
    userID,
    final_rank,
    recommended_movieID,
    recommended_title,
    ROUND(content_score, 4) AS content_score,
    ROUND(collaborative_score, 4) AS collaborative_score,
    ROUND(final_score, 4) AS final_score
FROM user_hybrid_recommendations_top20
WHERE userID = 54
  AND recommended_by_both = 1
ORDER BY final_rank;


/*
Query 5: Breakdown of recommendation source types
*/
SELECT
    model_source,
    COUNT(*) AS row_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_rows
FROM user_hybrid_recommendations_top20
GROUP BY model_source
ORDER BY row_count DESC;


/*
Query 6: Users with fewer than 20 hybrid recommendations
*/
SELECT
    userID,
    COUNT(*) AS recommendation_count
FROM user_hybrid_recommendations_top20
GROUP BY userID
HAVING COUNT(*) < 20
ORDER BY recommendation_count ASC, userID;


/*
Query 7: Highest-scoring hybrid recommendations overall
*/
SELECT
    userID,
    final_rank,
    recommended_movieID,
    recommended_title,
    model_source,
    ROUND(final_score, 4) AS final_score
FROM user_hybrid_recommendations_top20
ORDER BY final_score DESC, userID, final_rank
LIMIT 25;


/*
Query 8: Compare hybrid scores for one user
*/
SELECT
    h.userID,
    h.final_rank,
    h.recommended_movieID,
    h.recommended_title,
    ROUND(h.content_score, 4) AS hybrid_content_score,
    ROUND(h.collaborative_score, 4) AS hybrid_collaborative_score,
    ROUND(h.final_score, 4) AS hybrid_final_score,
    h.model_source
FROM user_hybrid_recommendations_top20 h
WHERE h.userID = 54
ORDER BY h.final_rank;


/*
Query 9: Users who have hybrid recommendations but no overlap
*/
SELECT
    userID,
    COUNT(*) AS recommendation_count,
    SUM(recommended_by_both) AS overlap_count
FROM user_hybrid_recommendations_top20
GROUP BY userID
HAVING SUM(recommended_by_both) = 0
ORDER BY recommendation_count DESC, userID;


/*
Query 10: Average hybrid score by final rank
*/
SELECT
    final_rank,
    ROUND(AVG(final_score), 4) AS avg_final_score,
    ROUND(AVG(content_score), 4) AS avg_content_score,
    ROUND(AVG(collaborative_score), 4) AS avg_collaborative_score
FROM user_hybrid_recommendations_top20
GROUP BY final_rank
ORDER BY final_rank;


/*
Query 11: Join hybrid recommendations to movie metadata
*/
SELECT
    h.userID,
    h.final_rank,
    h.recommended_movieID,
    h.recommended_title,
    m.genres_comma,
    m.avg_rating,
    m.rating_count,
    h.model_source,
    ROUND(h.final_score, 4) AS final_score
FROM user_hybrid_recommendations_top20 h
LEFT JOIN movie_content_clean m
    ON h.recommended_movieID = m.movieID
WHERE h.userID = 54
ORDER BY h.final_rank;


/*
Query 12: Users with no hybrid recommendations
*/
SELECT
    u.userID
FROM (
    SELECT DISTINCT userID
    FROM user_movie_interactions
) u
LEFT JOIN (
    SELECT DISTINCT userID
    FROM user_hybrid_recommendations_top20
) h
    ON u.userID = h.userID
WHERE h.userID IS NULL
ORDER BY u.userID;


/*
Query 13: Ten random users and all of their hybrid recommendations
*/
WITH random_users AS (
    SELECT DISTINCT userID
    FROM user_hybrid_recommendations_top20
    ORDER BY RANDOM()
    LIMIT 10
)
SELECT
    h.userID,
    h.final_rank,
    h.recommended_movieID,
    h.recommended_title,
    ROUND(h.content_score, 4) AS content_score,
    ROUND(h.collaborative_score, 4) AS collaborative_score,
    h.recommended_by_both,
    h.model_source,
    ROUND(h.final_score, 4) AS final_score
FROM user_hybrid_recommendations_top20 h
INNER JOIN random_users r
    ON h.userID = r.userID
ORDER BY h.userID, h.final_rank;


/*
Query 14: Ten random users and hybrid recommendations with movie metadata
*/
WITH random_users AS (
    SELECT DISTINCT userID
    FROM user_hybrid_recommendations_top20
    ORDER BY RANDOM()
    LIMIT 10
)
SELECT
    h.userID,
    h.final_rank,
    h.recommended_movieID,
    h.recommended_title,
    m.genres_comma,
    ROUND(m.avg_rating, 2) AS avg_rating,
    m.rating_count,
    h.model_source,
    ROUND(h.final_score, 4) AS final_score
FROM user_hybrid_recommendations_top20 h
INNER JOIN random_users r
    ON h.userID = r.userID
LEFT JOIN movie_content_clean m
    ON h.recommended_movieID = m.movieID
ORDER BY h.userID, h.final_rank;


/*
Query 15: Top 1 hybrid recommendation for ten random users
*/
WITH random_users AS (
    SELECT DISTINCT userID
    FROM user_hybrid_recommendations_top20
    ORDER BY RANDOM()
    LIMIT 10
)
SELECT
    h.userID,
    h.recommended_movieID,
    h.recommended_title,
    h.model_source,
    ROUND(h.final_score, 4) AS final_score
FROM user_hybrid_recommendations_top20 h
INNER JOIN random_users r
    ON h.userID = r.userID
WHERE h.final_rank = 1
ORDER BY h.userID;
