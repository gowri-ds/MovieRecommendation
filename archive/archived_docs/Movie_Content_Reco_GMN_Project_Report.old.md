# GMN Content-Based Movie Recommendation System Project Report

## Abstract

This project develops and evaluates a content-based movie recommendation system built on top of a SQLite database. The system compares two primary content modeling approaches: a TF-IDF text-based similarity model and a Genre One-Hot Encoding (OHE) similarity model. On top of these base recommenders, the project implements two router strategies: a weighted hybrid router and a confidence-based hybrid router. The full pipeline produces movie-to-movie similarity tables, user-level recommendation tables, hybrid recommendation tables, offline evaluation outputs, supporting SQL analysis assets, and two Flask-based user interfaces for interactive exploration. In offline leave-one-out evaluation, the Genre OHE model achieved the strongest hit rate at 10, followed by the confidence-based hybrid router, the TF-IDF model, and the weighted hybrid router. The project demonstrates a complete recommender workflow from feature engineering through evaluation and presentation, while also highlighting the limitations of purely content-based recommendation.

## 1. Introduction

Recommender systems help users discover relevant content in large catalogs. In the movie domain, recommendation quality can be improved by analyzing item attributes such as genres, text descriptions, and metadata. This project focuses on content-based recommendation, meaning that recommendations are generated from movie features rather than from user-to-user behavioral similarity.

The main goal of this project is to build a practical recommendation pipeline that can:

- compute movie-to-movie similarity,
- transform those similarities into user-level recommendations,
- compare multiple recommendation strategies,
- evaluate them with an offline testing framework, and
- expose the results through a web interface.

The project uses a staged pipeline implemented in Python and SQLite. Each stage creates permanent output tables so that the next stage can reuse prior results efficiently.

## 2. Project Objectives

The objectives of the project were to:

- build a TF-IDF based content similarity model using movie text features,
- build a Genre OHE similarity model using genre membership alone,
- generate user-level recommendations from each similarity model,
- combine both recommenders through hybrid routing strategies,
- evaluate the models using a consistent leave-one-out offline design,
- provide an interactive interface for recommendations and similarity lookup.

## 3. Data and Environment

The recommendation pipeline uses a SQLite database located at:

`G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db`

Important source tables include:

- `movie_content_clean`
- `vw_movie_content_features`
- `user_movie_interactions`

Important generated tables include:

- `movie_content_similarity_top20`
- `movie_genre_ohe_similarity_top20`
- `user_content_recommendations_top20`
- `user_content_recommendations_genre_ohe_top20`
- `user_hybrid_recommendations_top20`
- `user_confidence_hybrid_recommendations_top20`
- `recommender_offline_eval_user_results`
- `recommender_offline_eval_summary`

The implementation uses:

- `pandas` for data manipulation,
- `sqlite3` for database access,
- `scikit-learn` for vectorization and cosine similarity,
- `Flask` for the user interfaces.

The repository also includes supporting SQL files in the `sql/` folder for setup, testing, validation, and final reporting queries.

## 4. Methodology

### 4.1 TF-IDF Movie Similarity Model

The TF-IDF model uses the `combined_text` field from the movie feature layer. This field acts as a textual fingerprint for each movie by combining descriptive content into a single text representation. The script transforms this text using TF-IDF vectorization and computes cosine similarity across movie pairs.

For each movie, the model stores the top 20 most similar movies in `movie_content_similarity_top20`.

Strengths:

- captures richer textual nuance,
- can identify similarity beyond exact genre overlap,
- supports more detailed content matching.

Weaknesses:

- may over-emphasize repeated names or keywords,
- depends heavily on text quality,
- can introduce noisy similarity when metadata is inconsistent.

### 4.2 Genre One-Hot Encoding Similarity Model

The Genre OHE model uses genre membership as structured features. Each movie is converted into a binary vector indicating whether it belongs to each genre. Cosine similarity is then computed over these one-hot encoded genre vectors.

For each movie, the model stores the top 20 most similar movies in `movie_genre_ohe_similarity_top20`.

Strengths:

- simple and interpretable,
- stable and easy to explain,
- less sensitive to noisy text fields.

Weaknesses:

- less nuanced than TF-IDF,
- only captures broad genre overlap,
- cannot distinguish movies with similar genres but very different tone or style.

### 4.3 User-Level Recommendation Generation

For both TF-IDF and Genre OHE, user-level recommendations are built from `user_movie_interactions`. Movies rated at or above `4.0` are treated as liked items. For each user:

1. collect the user’s liked movies,
2. retrieve the top similar movies for each liked movie,
3. remove movies the user has already interacted with,
4. aggregate candidate scores across supporting liked movies,
5. rank the top 20 recommendations for that user.

This process generates:

- `user_content_recommendations_top20` for TF-IDF,
- `user_content_recommendations_genre_ohe_top20` for Genre OHE.

The recommendation score for a user-movie pair is the summed similarity score across all supporting liked movies.

### 4.4 Weighted Hybrid Router

The weighted hybrid router combines the user-level TF-IDF and Genre OHE outputs after normalizing scores within each model for each user. The final score is:

`final_score = 0.7 * tfidf_score_norm + 0.3 * ohe_score_norm + 0.05 * overlap_bonus`

where the overlap bonus is applied when both models recommend the same movie.

This approach is straightforward and gives TF-IDF more influence while still allowing Genre OHE to contribute support. The output table is `user_hybrid_recommendations_top20`.

### 4.5 Confidence-Based Hybrid Router

The confidence-based hybrid router uses a more adaptive rule set. Instead of applying the same weights to every recommendation, it first normalizes both models’ scores and then assigns each candidate movie to a confidence bucket based on the strength of the TF-IDF signal.

Key parameters used by the router are:

- strong TF-IDF threshold: `0.50`
- medium TF-IDF threshold: `0.20`
- strong TF-IDF weight: `0.80`
- medium TF-IDF weight: `0.65`
- strong OHE weight: `0.20`
- medium OHE weight: `0.35`
- overlap bonus: `0.08`
- OHE-only penalty factor: `0.85`

The confidence buckets are:

- high TF-IDF confidence,
- medium TF-IDF confidence,
- OHE fallback,
- low mixed confidence,
- low TF-IDF-only confidence,
- low confidence.

This router trusts TF-IDF more when the normalized TF-IDF signal is strong, falls back to Genre OHE when TF-IDF is absent, and rewards overlap when both models agree. The output table is `user_confidence_hybrid_recommendations_top20`.

## 5. System Architecture

The project follows a staged design:

1. movie feature preparation in SQLite,
2. movie-to-movie similarity generation,
3. user-level recommendation generation,
4. hybrid routing,
5. offline evaluation,
6. SQL-based testing, validation, and reporting,
7. web-based presentation.

This structure improves traceability because each output table can be inspected independently. It also separates pipeline logic, applications, documentation, and SQL support files into clearer repo sections.

## 6. User Interface

The project includes two Flask applications:

- `apps/Movie_Content_Reco_GMN_App_Purple_Lilac.py`
- `apps/Movie_Content_Reco_GMN_App_Matrix.py`

The apps allow users to:

- request recommendations for a selected `userID`,
- choose among TF-IDF, Genre OHE, Weighted Hybrid, and Confidence Hybrid outputs,
- inspect movie-to-movie similarity,
- view movie metadata,
- display poster images and external links.

This interface makes the recommendation system easier to demonstrate and supports both technical and non-technical project audiences.

## 7. Offline Evaluation Design

The project evaluates all four approaches using a leave-one-out strategy.

Evaluation rules:

- a liked movie is defined as a rating `>= 4.0`,
- users must have at least `5` liked movies to be eligible,
- one liked movie per eligible user is held out,
- recommendations are rebuilt from the remaining liked movies,
- a hit is recorded if the held-out movie appears in the top `10`.

The evaluation compares:

- `tfidf_model`
- `genre_ohe_model`
- `weighted_hybrid_router`
- `confidence_hybrid_router`

Metrics written to the evaluation summary include:

- hit rate at K,
- precision at K,
- recall at K,
- mean reciprocal rank,
- normalized discounted cumulative gain.

## 8. Results

Latest offline evaluation summary:

- eligible users: `603`
- `genre_ohe_model`: hit rate@10 = `0.0100`
- `confidence_hybrid_router`: hit rate@10 = `0.0083`
- `tfidf_model`: hit rate@10 = `0.0050`
- `weighted_hybrid_router`: hit rate@10 = `0.0033`

These results indicate that:

- the Genre OHE model performed best in this offline test,
- the confidence-based router improved on the weighted hybrid router,
- the TF-IDF model did not outperform the simpler Genre OHE baseline,
- all methods achieved low absolute hit rates.

## 9. Discussion

One of the most important findings in this project is that the simpler Genre OHE model outperformed the richer TF-IDF model in offline evaluation. A likely explanation is that genre similarity provides a stable and reliable signal for broad movie preference, while TF-IDF may introduce noise from repeated names, metadata artifacts, or overly specific text overlap.

The confidence-based router performed better than the fixed weighted hybrid because it adapts the scoring rule instead of assuming the same blend is optimal for every movie. This supports the idea that confidence-aware hybrid routing is more effective than a static weighted blend in this project setting.

At the same time, none of the methods achieved strong predictive performance. This highlights an important limitation of content-based recommendation: it can struggle to capture taste patterns that are better explained by collaborative behavior or richer semantic representations.

## 10. Limitations

The project has several limitations:

- it is content-based only and does not use collaborative filtering,
- TF-IDF can overweight repeated tokens or inconsistent metadata,
- Genre OHE is interpretable but coarse,
- the candidate pool is limited by top-20 similarity tables,
- hybrid weights and thresholds are hand-tuned,
- offline accuracy is low across all evaluated models.

## 11. Future Improvements

Future work could improve the system by:

- strengthening `combined_text` and movie metadata quality,
- expanding similarity candidate pools beyond top 20,
- weighting stronger user ratings more heavily,
- tuning hybrid thresholds and weights systematically,
- adding reranking features such as support count or popularity smoothing,
- replacing or extending TF-IDF with embeddings,
- integrating collaborative filtering into a larger hybrid recommender.

## 12. Conclusion

This project delivers a complete content-based recommendation pipeline, from movie similarity generation through user recommendation, hybrid routing, evaluation, SQL-based validation, and user interface delivery. The work demonstrates strong system design, reproducible table-based outputs, and thoughtful comparison across multiple recommendation strategies.

Among the evaluated methods, Genre OHE produced the strongest offline performance, while the confidence-based hybrid router provided the best hybrid result. Although overall accuracy remains modest, the project establishes a solid foundation for future recommender development and offers a clear path toward more advanced hybrid or collaborative approaches.

## Appendix: Key Files

Pipeline:

- `pipeline/Movie_Content_Reco_GMN_PL2.py`
- `pipeline/Movie_Content_Reco_GMN_PL2B_Genre_OHE.py`
- `pipeline/Movie_Content_Reco_GMN_PL4.py`
- `pipeline/Movie_Content_Reco_GMN_PL4B_Genre_OHE.py`
- `pipeline/Movie_Content_Reco_GMN_PL6_A_HybridRouter.py`
- `pipeline/Movie_Content_Reco_GMN_PL6_B_ConfidenceRouter.py`
- `pipeline/Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py`

Apps:

- `apps/Movie_Content_Reco_GMN_App_Purple_Lilac.py`
- `apps/Movie_Content_Reco_GMN_App_Matrix.py`

SQL:

- `sql/Movie_Content_Reco_GMN_PL1_SQL_Setup.sql`
- `sql/Movie_Content_Reco_GMN_PL4_SQL_Testing_Queries.sql`
- `sql/Movie_Content_Reco_GMN_PL5_A_SQL_Model_Comparison.sql`
- `sql/Movie_Content_Reco_GMN_PL5_B_SQL_Model_Validation.sql`
- `sql/Movie_Content_Reco_GMN_PL8_SQL_Final_Output_Queries.sql`
