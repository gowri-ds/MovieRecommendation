/*
========================================================================
CONTENT PIPELINE SQL TESTING QUERIES
========================================================================
Purpose:
    Validate the simplified content pipeline, which now uses the
    TMDB-enriched feature view when available.

Core objects:
    movie_content_clean
    vw_movie_content_features
    vw_movie_content_features_enriched
    movie_content_similarity_top20
    user_content_recommendations_top20
========================================================================
*/

/*
Query 1: Confirm the base and enriched content views exist
*/
SELECT name, type
FROM sqlite_master
WHERE type IN ('table', 'view')
  AND name IN (
      'movie_content_clean',
      'vw_movie_content_features',
      'vw_movie_content_features_enriched',
      'movie_content_similarity_top20',
      'user_content_recommendations_top20'
  )
ORDER BY type, name;

/*
Query 2: Quick title lookup
*/
SELECT movieID, title
FROM movie_content_clean
WHERE title LIKE '%home%'
ORDER BY title, movieID;

/*
Query 3: Check whether enrichment rows have been attached to the content layer
*/
SELECT
    movieID,
    title,
    SUBSTR(combined_text, 1, 120) AS combined_text_preview
FROM vw_movie_content_features_enriched
LIMIT 10;

/*
Query 4: Movie-to-movie content similarity for one movie
*/
SELECT
    base_movieID,
    base_title,
    similar_movieID,
    similar_title,
    ROUND(similarity_score, 4) AS similarity_score,
    similarity_rank
FROM movie_content_similarity_top20
WHERE base_movieID = 586
ORDER BY similarity_rank;

/*
Query 5: User-level content recommendations
*/
SELECT
    userID,
    recommended_movieID,
    recommended_title,
    ROUND(recommendation_score, 4) AS recommendation_score,
    supporting_liked_movies,
    recommendation_rank
FROM user_content_recommendations_top20
WHERE userID = 1
ORDER BY recommendation_rank;

/*
Query 6: Ranking logic validation
*/
SELECT
    userID,
    recommended_movieID,
    recommended_title,
    ROUND(recommendation_score, 4) AS recommendation_score,
    supporting_liked_movies,
    recommendation_rank
FROM user_content_recommendations_top20
WHERE userID = 1
ORDER BY
    recommendation_score DESC,
    supporting_liked_movies DESC,
    recommended_title
LIMIT 10;

/*
Query 7: Inspect user interaction source rows
*/
SELECT *
FROM user_movie_interactions
LIMIT 25;
