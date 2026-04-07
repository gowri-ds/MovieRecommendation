# GMN Content Recommendation Pipeline

This project builds and compares several content-based movie recommendation approaches on top of a SQLite database.

Core workflows:
- TF-IDF movie similarity and user recommendation
- Genre OHE movie similarity and user recommendation
- Weighted hybrid router
- Confidence-based hybrid router
- Offline evaluation
- Two Flask UI apps

Database used:
- `G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db`

## File Guide

Model and router scripts:
- `Movie_Content_Reco_GMN_PL2.py`: TF-IDF movie-to-movie similarity
- `Movie_Content_Reco_GMN_PL4.py`: TF-IDF user recommendations
- `Movie_Content_Reco_GMN_PL2B_Genre_OHE.py`: Genre OHE movie similarity
- `Movie_Content_Reco_GMN_PL4B_Genre_OHE.py`: Genre OHE user recommendations
- `Movie_Content_Reco_GMN_PL6_A_HybridRouter.py`: weighted hybrid router
- `Movie_Content_Reco_GMN_PL6_B_ConfidenceRouter.py`: confidence-based hybrid router
- `Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py`: offline evaluation

UI files:
- `GMN_Purple_Lilac_Content_Based_Reco.py`: main purple/lilac Flask UI
- `matrixmatchmakers_contentbasedreco.py`: Matrix-themed Flask UI
- `app.py`: compatibility wrapper for the main UI

Frontend assets:
- `templates/index.html`
- `templates/matrix_index.html`
- `static/styles.css`
- `static/matrix_styles.css`

Support files:
- `requirements.txt`
- `.gitignore`

## Naming Convention

Project script naming follows the pipeline stage:
- `PL2`: movie similarity build
- `PL4`: user recommendation build
- `PL6`: router layer
- `PL7`: evaluation

Suffixes:
- no suffix: TF-IDF path
- `B_Genre_OHE`: genre one-hot encoding path
- `A_HybridRouter`: weighted hybrid router
- `B_ConfidenceRouter`: confidence-based hybrid router

## Main SQLite Tables

Similarity tables:
- `movie_content_similarity_top20`
- `movie_genre_ohe_similarity_top20`

User recommendation tables:
- `user_content_recommendations_top20`
- `user_content_recommendations_genre_ohe_top20`
- `user_hybrid_recommendations_top20`
- `user_confidence_hybrid_recommendations_top20`

Evaluation tables:
- `recommender_offline_eval_user_results`
- `recommender_offline_eval_summary`

## What Each Approach Does

TF-IDF:
- uses `combined_text`
- captures richer text-based similarity
- can over-weight repeated names or keywords

Genre OHE:
- uses genre one-hot encoding
- easier to explain
- less nuanced than TF-IDF

Weighted hybrid router:
- blends normalized TF-IDF and Genre OHE user-level scores
- adds a small overlap bonus when both models recommend the same movie

Confidence hybrid router:
- uses normalized scores and confidence buckets
- trusts stronger TF-IDF evidence more
- uses Genre OHE as fallback when TF-IDF is missing

## UI Apps

Main UI:
- `py GMN_Purple_Lilac_Content_Based_Reco.py`

Matrix UI:
- `py matrixmatchmakers_contentbasedreco.py`

Install dependencies first:
- `py -m pip install -r requirements.txt`

Then open:
- `http://127.0.0.1:5000`

Both UIs support:
- user recommendation flow
- movie similarity flow
- poster images
- IMDb-linked poster tiles
- movie metadata from `movie_content_clean`

## Offline Evaluation

The evaluation script uses a leave-one-out design:
- liked movies are ratings `>= 4.0`
- users need at least `5` liked movies
- one liked movie is held out per eligible user
- recommendations are built from the remaining liked movies
- evaluation checks whether the held-out movie appears in top `10`

Latest summary:
- eligible users: `603`
- `genre_ohe_model`: hit rate@10 = `0.0100`
- `confidence_hybrid_router`: hit rate@10 = `0.0083`
- `tfidf_model`: hit rate@10 = `0.0050`
- `weighted_hybrid_router`: hit rate@10 = `0.0033`

Interpretation:
- Genre OHE performed best on this leave-one-out test
- confidence routing outperformed the weighted hybrid router
- all methods had low hit rates, so the system is operational but still limited in predictive accuracy

## Limitations

- TF-IDF can over-weight repeated metadata terms
- Genre OHE is easier to explain but less granular
- the project is content-based only and does not use collaborative filtering
- current validation is strong structurally, but predictive accuracy still has room to improve
