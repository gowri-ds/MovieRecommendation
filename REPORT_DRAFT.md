# GMN Content-Based Movie Recommendation System Report

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

The project was designed around the following objectives:

- Build a TF-IDF based content similarity model using movie text features.
- Build a Genre OHE based similarity model using genre membership alone.
- Generate user-level recommendations from each similarity model.
- Combine both recommenders using hybrid routing strategies.
- Evaluate all approaches using a consistent leave-one-out offline design.
- Provide an interface for viewing recommendations and movie similarity results.

## 3. Data and System Environment

The recommendation pipeline uses a SQLite database located at:

`G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db`

The project reads from and writes to several database tables. Important source tables include:

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

The full implementation is written in Python using:

- `pandas` for data manipulation,
- `sqlite3` for database access,
- `scikit-learn` for TF-IDF vectorization and cosine similarity,
- `Flask` for the web interface.

The repository also includes supporting SQL files in the `sql/` folder for setup, testing, comparison, validation, and final reporting queries.

## 4. Methodology

### 4.1 TF-IDF Movie Similarity Model

The TF-IDF model uses the `combined_text` field from the movie feature layer. This field acts as a textual fingerprint for each movie by combining descriptive content into a single text representation. The script transforms this text using TF-IDF vectorization and then computes cosine similarity across all movie pairs.

For each movie, the model keeps the top 20 most similar movies and writes the results to `movie_content_similarity_top20`.

Strengths of this approach:

- captures richer textual nuance,
- can identify similarity beyond exact genre overlap,
- supports more detailed content matching.

Weaknesses of this approach:

- may over-emphasize repeated names or keywords,
- depends heavily on text quality,
- may introduce noisy similarity when metadata is inconsistent.

### 4.2 Genre One-Hot Encoding Similarity Model

The Genre OHE model uses genre membership as structured features. Each movie is converted into a binary vector indicating whether it belongs to each genre. Cosine similarity is then computed over these one-hot encoded genre vectors.

For each movie, the model stores the top 20 most similar movies in `movie_genre_ohe_similarity_top20`.

Strengths of this approach:

- simple and interpretable,
- stable and easy to explain,
- less sensitive to noisy text fields.

Weaknesses of this approach:

- less nuanced than TF-IDF,
- only captures broad genre overlap,
- cannot distinguish movies with similar genres but very different style or themes.

### 4.3 User-Level Recommendation Generation

For both TF-IDF and Genre OHE, user-level recommendations are built from `user_movie_interactions`. Movies rated at or above `4.0` are treated as liked items. For each user:

1. The system collects the user's liked movies.
2. It retrieves the top similar movies for each liked movie.
3. It removes movies the user has already interacted with.
4. It aggregates candidate scores across supporting liked movies.
5. It ranks the top 20 recommendations for that user.

This process generates:

- `user_content_recommendations_top20` for TF-IDF
- `user_content_recommendations_genre_ohe_top20` for Genre OHE

The recommendation score for a user-movie pair is the summed similarity score across all supporting liked movies. Additional fields such as supporting liked movie count, average supporting rating, and support titles make the recommendations easier to interpret.

### 4.4 Weighted Hybrid Router

The weighted hybrid router combines the user-level TF-IDF and Genre OHE outputs after normalizing scores within each model for each user. The final score is:

`final_score = 0.7 * tfidf_score_norm + 0.3 * ohe_score_norm + 0.05 * overlap_bonus`

where the overlap bonus is applied when both models recommend the same movie.

This approach is straightforward and gives TF-IDF more influence while still allowing Genre OHE to contribute supporting evidence. The output table is `user_hybrid_recommendations_top20`.

### 4.5 Confidence-Based Hybrid Router

The confidence-based hybrid router uses a more adaptive rule set. Instead of applying the same weights to every recommendation, it first normalizes both models' scores and then assigns each candidate movie to a confidence bucket based on the strength of the TF-IDF signal.

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

The pipeline follows a layered design:

1. Movie feature preparation in SQLite.
2. Movie-to-movie similarity generation.
3. User-level recommendation generation.
4. Hybrid routing.
5. Offline evaluation.
6. SQL-based testing, validation, and reporting.
7. Web-based presentation.

This staged structure improves traceability because each output table can be inspected independently. It also makes the project easier to debug and explain.

Supporting SQL scripts strengthen this architecture by separating database setup, testing queries, model comparison, validation, and final reporting from the Python model-building workflow.

## 6. User Interface

The project includes two Flask applications:

- `GMN_Purple_Lilac_Content_Based_Reco.py`
- `matrixmatchmakers_contentbasedreco.py`

The main Flask UI allows users to:

- request recommendations for a selected `userID`,
- choose among TF-IDF, Genre OHE, Weighted Hybrid, and Confidence Hybrid outputs,
- inspect movie-to-movie similarity,
- view movie metadata,
- display poster images and external links.

This interface makes the recommendation system more accessible to non-technical users and demonstrates how the database outputs can support an end-user application.

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

The latest summary recorded in the project materials reports:

- eligible users: `603`
- `genre_ohe_model`: hit rate@10 = `0.0100`
- `confidence_hybrid_router`: hit rate@10 = `0.0083`
- `tfidf_model`: hit rate@10 = `0.0050`
- `weighted_hybrid_router`: hit rate@10 = `0.0033`

These results indicate that:

- the Genre OHE model performed best in this offline test,
- the confidence-based router improved on the weighted hybrid router,
- the TF-IDF model alone did not outperform the simpler Genre OHE baseline,
- all methods achieved relatively low absolute hit rates.

The low scores suggest that the pipeline is functioning correctly from a systems perspective, but recommendation accuracy remains limited. This is consistent with a content-only recommendation design, especially when evaluation is based on a strict holdout protocol.

## 9. Discussion

One of the most interesting findings in this project is that the simpler Genre OHE model outperformed the richer TF-IDF model in offline evaluation. A likely explanation is that genre similarity provides a stable and reliable signal for broad movie preference, while TF-IDF may introduce noise from repeated names, metadata artifacts, or overly specific text overlap.

The confidence-based router performed better than the fixed weighted hybrid because it adapts the scoring rule instead of assuming the same blend is optimal for every movie. This is a meaningful design improvement because it treats strong TF-IDF evidence differently from weak TF-IDF evidence and provides a fallback path when only Genre OHE is available.

Even so, none of the methods achieved strong predictive performance. This highlights a core limitation of content-based recommendation: it can struggle to capture taste patterns that are better explained by collaborative signals, temporal behavior, or richer semantic embeddings.

## 10. Limitations

This project has several limitations:

- it is content-based only and does not use collaborative filtering,
- TF-IDF can overweight repeated tokens or inconsistent metadata,
- Genre OHE is interpretable but coarse,
- offline accuracy is low across all models,
- the system depends on the quality and completeness of the underlying database.

In addition, the leave-one-out design is useful for comparison, but it does not fully represent how real users interact with a recommendation interface over time.

## 11. Future Improvements

Several extensions could improve the system:

- add collaborative filtering or matrix factorization,
- replace basic TF-IDF with embeddings from modern language models,
- tune thresholds and weights systematically instead of manually,
- incorporate additional metadata such as cast, directors, keywords, and plot summaries,
- evaluate with more ranking metrics and broader test designs,
- personalize hybrid routing based on user history characteristics,
- add explanation panels in the UI showing why each movie was recommended.

## 12. Conclusion

This project delivers a full content-based recommendation pipeline, from movie similarity generation through user recommendation, hybrid routing, evaluation, SQL-based validation, and user interface delivery. The work demonstrates strong system design, reproducible table-based outputs, and thoughtful comparison across multiple recommendation strategies.

Among the evaluated methods, Genre OHE produced the strongest offline performance, while the confidence-based hybrid router provided the best hybrid result. Although overall accuracy remains modest, the project establishes a solid foundation for future recommender development and offers a clear path toward more advanced hybrid or collaborative approaches.

## Appendix: Key Pipeline Files

- `Movie_Content_Reco_GMN_PL2.py`
- `Movie_Content_Reco_GMN_PL2B_Genre_OHE.py`
- `Movie_Content_Reco_GMN_PL4.py`
- `Movie_Content_Reco_GMN_PL4B_Genre_OHE.py`
- `Movie_Content_Reco_GMN_PL6_A_HybridRouter.py`
- `Movie_Content_Reco_GMN_PL6_B_ConfidenceRouter.py`
- `Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py`
- `GMN_Purple_Lilac_Content_Based_Reco.py`
- `matrixmatchmakers_contentbasedreco.py`

## Appendix: Supporting SQL Files

- `sql/Movie_Content_Reco_GMN_PL1_SQL_Setup.sql`
- `sql/Movie_Content_Reco_GMN_PL4_SQL_Testing_Queries.sql`
- `sql/Movie_Content_Reco_GMN_PL5_A_SQL_Model_Comparison.sql`
- `sql/Movie_Content_Reco_GMN_PL5_B_SQL_Model_Validation.sql`
- `sql/Movie_Content_Reco_GMN_PL8_SQL_Final_Output_Queries.sql`
