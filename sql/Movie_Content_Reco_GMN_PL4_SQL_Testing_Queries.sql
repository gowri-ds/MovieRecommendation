---- Movie title Lookup that has "home" in their title

SELECT movieID, title
FROM movie_content_clean
WHERE title LIKE '%home%';

---- # Movie title Lookup that has "home" in their title
SELECT count(*)
FROM movie_content_clean
WHERE title LIKE '%home%';

---- Movie to Movie Similarity  
SELECT *
FROM movie_content_similarity_top20
WHERE base_movieID = 586
ORDER BY similarity_rank;

---- User Recommendation 
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

--- Ranking logic Validation

SELECT *
FROM user_content_recommendations_top20
WHERE userId = 1
ORDER BY 
    recommendation_score DESC,
    supporting_liked_movies DESC,
    recommended_title
LIMIT 10;

----
select * from user_movie_interactions;
