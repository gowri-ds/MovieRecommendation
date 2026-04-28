/* ------------------------------------------------------------
Query 1: Content recommendations for one user
------------------------------------------------------------ */
SELECT
    userID,
    recommended_movieID,
    recommended_title,
    recommendation_score,
    recommendation_rank
FROM user_content_recommendations_top20
WHERE userID = 54
ORDER BY recommendation_rank;

/* ------------------------------------------------------------
Query 2: Collaborative recommendations for one user
------------------------------------------------------------ */
SELECT
    userID,
    recommended_movieID,
    recommended_title,
    recommendation_score,
    recommendation_rank
FROM user_collaborative_knn_recommendations_top20
WHERE userID = 54
ORDER BY recommendation_rank;

/* ------------------------------------------------------------
Query 3: Hybrid recommendations for one user
------------------------------------------------------------ */
SELECT
    userID,
    final_rank,
    recommended_movieID,
    recommended_title,
    content_score,
    collaborative_score,
    recommended_by_both,
    model_source,
    final_score
FROM user_hybrid_recommendations_top20
WHERE userID = 54
ORDER BY final_rank;

/* ------------------------------------------------------------
Query 4: Overlap between content and collaborative for one user
------------------------------------------------------------ */
SELECT
    userID,
    overlap_movieID,
    overlap_title,
    ROUND(content_recommendation_score, 4) AS content_score,
    ROUND(collaborative_recommendation_score, 4) AS collaborative_score,
    ROUND(hybrid_final_score, 4) AS hybrid_score
FROM user_model_overlap_detail
WHERE userID = 54
ORDER BY hybrid_score DESC, content_score DESC, collaborative_score DESC;

/* ------------------------------------------------------------
Query 5: Content similarity for one movie
------------------------------------------------------------ */
SELECT
    base_movieID,
    base_title,
    similar_movieID,
    similar_title,
    similarity_score,
    similarity_rank
FROM movie_content_similarity_top20
WHERE base_movieID = 1
ORDER BY similarity_rank;

/* ------------------------------------------------------------
Query 6: Preview the enriched content view feeding the content model
------------------------------------------------------------ */
SELECT
    movieID,
    title,
    tmdb_director,
    SUBSTR(overview, 1, 100) AS overview_preview,
    SUBSTR(combined_text, 1, 140) AS combined_text_preview
FROM vw_movie_content_features_enriched
LIMIT 10;
