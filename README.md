# GMN Content Recommendation Pipeline

This repository contains five Python scripts that build three related recommendation workflows on top of a SQLite database:

- a TF-IDF text-based pipeline
- a genre one-hot encoding (OHE) pipeline
- a hybrid router that blends both user-level models

## Files

- `Movie_Content_Reco_GMN_PL2.py`
  Builds a TF-IDF movie-to-movie similarity model from cleaned movie content features and writes the top 20 similar movies for each title to SQLite.

- `Movie_Content_Reco_GMN_PL4.py`
  Builds user-level content recommendations by combining user liked movies with the movie similarity table and writes the top 20 recommendations per user to SQLite.

- `Movie_Content_Reco_GMN_PL2B_Genre_OHE.py`
  Builds a movie-to-movie similarity model using genre one-hot encoding and writes the top 20 similar movies for each title to a separate SQLite table.

- `Movie_Content_Reco_GMN_PL4B_Genre_OHE.py`
  Builds user-level recommendations from the genre OHE similarity table and writes the top 20 recommendations per user to a separate SQLite table.

- `Movie_Content_Reco_GMN_PL6_A_HybridRouter.py`
  Builds hybrid user-level recommendations by blending normalized TF-IDF and genre OHE recommendation scores, adding a small overlap bonus when both models recommend the same movie, and writing the final ranked output to SQLite.

## Database

Both scripts use the SQLite database at:

`G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db`

## Generated Tables

### TF-IDF tables

#### `movie_content_similarity_top20`

Stores the top 20 most similar movies for each base movie.

Columns:
- `base_movieID`
- `base_title`
- `similar_movieID`
- `similar_title`
- `similarity_score`
- `similarity_rank`

#### `user_content_recommendations_top20`

Stores the top 20 content-based recommendations for each eligible user.

Columns:
- `userID`
- `recommended_movieID`
- `recommended_title`
- `recommendation_score`
- `supporting_liked_movies`
- `avg_supporting_rating`
- `recommendation_rank`
- `support_movie_ids`
- `support_movie_titles`

### Genre OHE tables

#### `movie_genre_ohe_similarity_top20`

Stores the top 20 most similar movies for each base movie using genre one-hot encoded features.

Columns:
- `base_movieID`
- `base_title`
- `similar_movieID`
- `similar_title`
- `similarity_score`
- `similarity_rank`

#### `user_content_recommendations_genre_ohe_top20`

Stores the top 20 genre-based recommendations for each eligible user.

Columns:
- `userID`
- `recommended_movieID`
- `recommended_title`
- `recommendation_score`
- `supporting_liked_movies`
- `avg_supporting_rating`
- `recommendation_rank`
- `support_movie_ids`
- `support_movie_titles`

### Hybrid table

#### `user_hybrid_recommendations_top20`

Stores the top 20 hybrid recommendations per user after combining the TF-IDF and genre OHE user-level outputs.

Columns:
- `userID`
- `recommended_movieID`
- `recommended_title`
- `tfidf_score`
- `ohe_score`
- `tfidf_score_norm`
- `ohe_score_norm`
- `recommended_by_both`
- `final_score`
- `model_source`
- `final_rank`

## Execution Summary

The scripts were run successfully on April 6, 2026.

Results:
- `movie_content_similarity_top20` contains `194,840` rows across `9,742` movies.
- Each movie received exactly `20` ranked similar-movie recommendations.
- `user_content_recommendations_top20` contains `12,180` rows across `609` users.
- Each eligible user received exactly `20` ranked recommendations.
- `movie_genre_ohe_similarity_top20` contains `194,160` rows across `9,708` movies.
- Each genre OHE movie received exactly `20` ranked similar-movie recommendations.

Example outputs:
- `Toy Story (1995)` matched strongly with `Toy Story 3 (2010)` and `Toy Story 2 (1999)`.
- For `userID = 1`, the top recommendation was `To Be or Not to Be (1942)`.
- In the genre OHE model, `Toy Story (1995)` matched with several titles that share the same genre profile, producing many `1.0` similarity scores.

## Model Notes

The TF-IDF pipeline uses `combined_text` and captures richer textual similarity from titles, genres, tags, and other descriptive content. This generally produces more nuanced matches, but it can also over-weight repeated keywords or names.

The genre OHE pipeline is intentionally simpler. It compares movies only on genre membership, which makes the model easier to explain but also less granular. Movies with identical genre combinations can receive identical similarity scores, often `1.0`.

The hybrid router combines both user-level models after normalizing each model's score range per user. This makes the blend more stable, because the raw TF-IDF and OHE recommendation scores are not naturally on the same numeric scale.

## Limitations

This model relies on TF-IDF features built from `combined_text`, so it can over-weight repeated keywords, names, or metadata tokens instead of deeper semantic meaning. One example is `Jumanji (1995)` matching with `Robin Williams: Live on Broadway (2002)`, which suggests actor-name overlap influenced the result.

The recommendation logic also treats ratings greater than or equal to `4.0` as a binary "liked" signal. That simplifies user preferences and can exclude users with weaker or sparse positive feedback. In this build, `610` users appeared in the interaction data, but only `609` received recommendations because one user had no ratings at or above the threshold.

Finally, all three workflows are content-based only. They do not use collaborative filtering, so they may miss useful patterns from similar-user behavior. The current validation confirms structural correctness and plausible examples, but it does not yet measure predictive accuracy with metrics such as precision, recall, or hit rate.
