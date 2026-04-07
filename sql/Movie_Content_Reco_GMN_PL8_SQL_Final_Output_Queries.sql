/*------------------------------------------------------------
Query 1: TF-IDF only recommendations for one user
Purpose:
- Returns the final Top-N recommendations for a single user
  from the TF-IDF content-based recommender.
- Uses similarity built from richer movie text/content features,
  so this is the “text-driven” recommendation output.

What it shows:
- userID: the target user
- recommended_movieID: movie being recommended
- recommended_title: movie title
- recommendation_score: final TF-IDF recommendation strength

Why we use it:
- Use this when you want recommendations coming only from
  the TF-IDF model, without involving OHE or hybrid logic.
- Good for showing the standalone performance of the
  text/content-based model.

Interpretation:
- Higher recommendation_score = stronger recommendation
- Results are sorted from strongest to weakest recommendation
  for user 54.
------------------------------------------------------------*/
SELECT
    userID,
    recommended_movieID,
    recommended_title,
    recommendation_score
FROM user_content_recommendations_top20
WHERE userID = 54
ORDER BY recommendation_score DESC, recommended_title;
/*------------------------------------------------------------
Query 2: OHE only recommendations for one user
Purpose:
- Returns the final Top-N recommendations for a single user
  from the One-Hot Encoding (OHE) genre-based recommender.
- This model relies more on structured genre/category overlap
  rather than richer text similarity.

What it shows:
- userID: the target user
- recommended_movieID: movie being recommended
- recommended_title: movie title
- recommendation_score: final OHE recommendation strength

Why we use it:
- Use this when you want recommendations coming only from
  the OHE/genre model.
- Good for comparing whether simple structured genre features
  behave differently from TF-IDF text features.

Interpretation:
- Higher recommendation_score = stronger recommendation
- Results are sorted from strongest to weakest recommendation
  for user 54.
------------------------------------------------------------*/
SELECT
    userID,
    recommended_movieID,
    recommended_title,
    recommendation_score
FROM user_content_recommendations_genre_ohe_top20
WHERE userID = 54
ORDER BY recommendation_score DESC, recommended_title;

/*------------------------------------------------------------
Query 3: Shared recommendations between TF-IDF and OHE
Purpose:
- Shows movies that both models recommended for the same user.
- This is the overlap view, useful for identifying agreement
  between the two standalone models.

What it shows:
- userID: the target user
- overlap_movieID: movie recommended by both models
- overlap_title: shared recommended title
- tfidf_score: recommendation strength from TF-IDF model
- ohe_score: recommendation strength from OHE model

Why we use it:
- Helps measure model agreement.
- Movies appearing here are often stronger candidates because
  both models independently selected them.
- Useful for explaining why a recommendation may be more reliable.

Interpretation:
- If a movie appears in this result, both models support it.
- Higher TF-IDF and OHE scores suggest stronger cross-model support.
- This query is especially useful before building hybrid logic.
------------------------------------------------------------*/
SELECT
    userID,
    overlap_movieID,
    overlap_title,
    ROUND(tfidf_recommendation_score, 4) AS tfidf_score,
    ROUND(ohe_recommendation_score, 4) AS ohe_score
FROM user_model_overlap_detail
WHERE userID = 54
ORDER BY tfidf_score DESC, ohe_score DESC;

/*------------------------------------------------------------
Query 4: Hybrid routing recommendations for one user
Purpose:
- Returns the final hybrid recommendation list for one user.
- Combines TF-IDF and OHE outputs into one ranked result set.
- The routing logic decides whether the recommendation came
  from TF-IDF only, OHE only, or both models together.

What it shows:
- userID: the target user
- final_rank: final recommendation order shown to the user
- recommended_movieID: movie being recommended
- recommended_title: movie title
- tfidf_score: score from TF-IDF model (if available)
- ohe_score: score from OHE model (if available)
- recommended_by_both: indicates whether both models recommended it
- model_source: shows which model or combination produced it
- final_score: combined score used for hybrid ranking

Why we use it:
- This is the practical recommendation query if you want a
  single final answer for the user.
- It balances the richer text-based model and the simpler
  structured genre model.

Interpretation:
- final_rank = display order of recommendations
- recommended_by_both = especially valuable because both models agree
- model_source helps explain whether the movie was selected from:
    1. TF-IDF only
    2. OHE only
    3. Both models
- final_score is the ranking score after hybrid combination.
------------------------------------------------------------*/
SELECT
    userID,
    final_rank,
    recommended_movieID,
    recommended_title,
    tfidf_score,
    ohe_score,
    recommended_by_both,
    model_source,
    final_score
FROM user_hybrid_recommendations_top20
WHERE userID = 1
ORDER BY final_rank;

/*------------------------------------------------------------
Query 5: Confidence-based hybrid routing recommendations
Purpose:
- Returns the final hybrid recommendation list for one user,
  but with an added confidence layer.
- In addition to combining TF-IDF and OHE, this query labels
  each recommendation by confidence level.

What it shows:
- userID: the target user
- final_rank: final recommendation order shown to the user
- recommended_movieID: movie being recommended
- recommended_title: movie title
- tfidf_score: score from TF-IDF model (if available)
- ohe_score: score from OHE model (if available)
- recommended_by_both: indicates whether both models recommended it
- model_source: shows which model or combination produced it
- confidence_bucket: internal confidence category
- confidence_label: readable confidence label (for example,
  High / Medium / Low depending on your logic)
- final_score: combined score used for final ranking

Why we use it:
- This is the most interpretable final recommendation query.
- It does not just recommend movies; it also tells us how much
  confidence we have in each recommendation.
- Very useful for presentation, reporting, and explaining
  recommendation reliability to your professor.

Interpretation:
- Recommendations supported by both models and/or strong scores
  will usually fall into a higher confidence bucket.
- Confidence labels help distinguish stronger recommendations
  from weaker or fallback recommendations.
- final_rank is the order you would present to the user.
------------------------------------------------------------*/
SELECT
    userID,
    final_rank,
    recommended_movieID,
    recommended_title,
    tfidf_score,
    ohe_score,
    recommended_by_both,
    model_source,
    confidence_bucket,
    confidence_label,
    final_score
FROM user_confidence_hybrid_recommendations_top20
WHERE userID = 1
ORDER BY final_rank;

select movieID, title from Movies where title like '%hannibal%';
/*------------------------------------------------------------
TF-IDF movie similarity for one base movie
Purpose:
- Shows the Top 20 most similar movies to one selected movie
  using the TF-IDF content-based similarity model.
- This model uses richer text/content features.

How to use:
- Replace 1 with any base_movieID you want to inspect.
------------------------------------------------------------*/
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

/*------------------------------------------------------------
OHE genre movie similarity for one base movie
Purpose:
- Shows the Top 20 most similar movies to one selected movie
  using the One-Hot Encoded genre similarity model.
- This model is based mainly on genre overlap.

How to use:
- Replace 1 with any base_movieID you want to inspect.
------------------------------------------------------------*/
SELECT
    base_movieID,
    base_title,
    similar_movieID,
    similar_title,
    similarity_score,
    similarity_rank
FROM movie_genre_ohe_similarity_top20
WHERE base_movieID = 1
ORDER BY similarity_rank;
