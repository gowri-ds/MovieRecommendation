/*
========================================================================
COLLABORATIVE KNN USER-USER SQL TESTING QUERIES
========================================================================
Purpose:
    Validate and inspect the output of the collaborative recommendation
    pipeline step.

Source table:
    user_collaborative_knn_recommendations_top20
========================================================================
*/

/*
Query 1: Confirm the output table exists
*/
SELECT name
FROM sqlite_master
WHERE type = 'table'
  AND name = 'user_collaborative_knn_recommendations_top20';


/*
Query 2: Overall summary
*/
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT userID) AS distinct_users,
    MIN(recommendation_rank) AS min_rank,
    MAX(recommendation_rank) AS max_rank
FROM user_collaborative_knn_recommendations_top20;


/*
Query 3: Top 10 recommendations for userID = 1
*/
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


/*
Query 4: Top 10 recommendations for userID = 400
*/
SELECT
    userID,
    recommended_movieID,
    recommended_title,
    ROUND(recommendation_score, 4) AS recommendation_score,
    recommendation_rank
FROM user_collaborative_knn_recommendations_top20
WHERE userID = 400
ORDER BY recommendation_rank
LIMIT 10;


/*
Query 5: Users with fewer than 20 recommendations
*/
SELECT
    userID,
    COUNT(*) AS recommendation_count
FROM user_collaborative_knn_recommendations_top20
GROUP BY userID
HAVING COUNT(*) < 20
ORDER BY recommendation_count ASC, userID;


/*
Query 6: Highest-scoring recommendations overall
*/
SELECT
    userID,
    recommended_movieID,
    recommended_title,
    ROUND(recommendation_score, 4) AS recommendation_score,
    recommendation_rank
FROM user_collaborative_knn_recommendations_top20
ORDER BY recommendation_score DESC
LIMIT 20;


/*
Query 7: Explain which similar users supported recommendations for userID = 1
*/
SELECT
    userID,
    recommended_title,
    ROUND(recommendation_score, 4) AS recommendation_score,
    supporting_liked_movies,
    support_movie_ids,
    support_movie_titles
FROM user_collaborative_knn_recommendations_top20
WHERE userID = 1
ORDER BY recommendation_rank
LIMIT 10;


/*
Query 8: Sanity check for duplicate ranks per user
Expected result:
    No rows returned
*/
SELECT
    userID,
    recommendation_rank,
    COUNT(*) AS row_count
FROM user_collaborative_knn_recommendations_top20
GROUP BY userID, recommendation_rank
HAVING COUNT(*) > 1;
