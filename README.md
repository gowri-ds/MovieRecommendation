# GMN Recommendation Pipeline

This repository contains the final simplified version of the GMN movie recommendation project. The active system has four recommendation layers:

- enriched content recommendations
- collaborative KNN recommendations
- a hybrid router that combines both signals
- a logistic like-prediction layer for final scoring

The active hybrid experience is exposed through the Flask app `Matrix Matchmakers`.

## Active Project Structure

### Pipeline

- `pipeline/Movie_Recommendation_GMN_PL0_Enrich.py`
  Adds TMDB metadata and builds enriched feature tables.
- `pipeline/Movie_Recommendation_GMN_PL2.py`
  Builds item-item content similarity from enriched text features.
- `pipeline/Movie_Recommendation_GMN_PL4.py`
  Builds user-level content recommendations.
- `pipeline/Movie_Collaborative_Reco_BBA_PL4C.py`
  Builds user-level collaborative KNN recommendations.
- `pipeline/Movie_Collaborative_Reco_BBA_PL4D_LeaveOneOut.py`
  Runs leave-one-out validation for the collaborative model.
- `pipeline/Movie_Recommendation_GMN_PL6_A_HybridRouter.py`
  Builds the hybrid recommendation table by blending content and collaborative outputs.
- `pipeline/Movie_Recommendation_GMN_PL7_Offline_Evaluation.py`
  Evaluates the active recommenders.
- `pipeline/Movie_Recommendation_GMN_PL8_A_LogisticLikePredictor.py`
  Trains the logistic like model and writes final probability-based recommendations.

### SQL

- `sql/Movie_Recommendation_GMN_PL1_SQL_Setup.sql`
- `sql/Movie_Recommendation_GMN_PL4_SQL_Testing_Queries.sql`
- `sql/Movie_Collaborative_Reco_GMN_PL4C_SQL_Testing_Queries.sql`
- `sql/Movie_Collaborative_Reco_GMN_PL4D_LeaveOneOut_SQL_Testing_Queries.sql`
- `sql/Movie_Recommendation_GMN_PL5_A_SQL_Model_Comparison.sql`
- `sql/Movie_Recommendation_GMN_PL5_B_SQL_Model_Validation.sql`
- `sql/Movie_Recommendation_GMN_PL8_SQL_Final_Output_Queries.sql`

### App Interface

- `apps/Movie_Recommendation_GMN_HybridRouter.py`
  Matrix Matchmakers hybrid app.

### App Support

- `apps/Movie_Recommendation_GMN_HybridRouter_Core.py`
  Shared hybrid UI logic, recommendation retrieval, and table rendering helpers.

### UI Assets

- `templates/`
- `static/`

### Documentation

- `docs/Movie_Recommendation_GMN_Project_Report.md`
- `docs/Movie_Recommendation_GMN_Pipeline.md`
- `docs/Movie_Recommendation_GMN_Pipeline_Report.md`
- `docs/Movie_Recommendation_GMN_Limitations_And_Improvements.md`
- `docs/Movie_Recommendation_GMN_Master_Sheet.md`

## Core Tables

### Content And Enrichment

- `movie_content_clean`
- `vw_movie_content_features`
- `movie_metadata_enriched`
- `vw_movie_content_features_enriched`
- `movie_content_similarity_top20`
- `user_content_recommendations_top20`

### Collaborative

- `user_collaborative_knn_recommendations_top20`
- `collaborative_knn_leave_one_out_user_results`
- `collaborative_knn_leave_one_out_summary`

### Hybrid And Evaluation

- `user_hybrid_recommendations_top20`
- `recommender_offline_eval_user_results`
- `recommender_offline_eval_summary`
- `user_hybrid_logistic_like_predictions_top20`
- `logistic_like_model_summary`

## Run Order

1. Run `sql/Movie_Recommendation_GMN_PL1_SQL_Setup.sql`
2. Run `py pipeline/Movie_Recommendation_GMN_PL0_Enrich.py`
3. Run `py pipeline/Movie_Recommendation_GMN_PL2.py`
4. Run `py pipeline/Movie_Recommendation_GMN_PL4.py`
5. Run `py pipeline/Movie_Collaborative_Reco_BBA_PL4C.py`
6. Run `py pipeline/Movie_Collaborative_Reco_BBA_PL4D_LeaveOneOut.py`
7. Run `py pipeline/Movie_Recommendation_GMN_PL6_A_HybridRouter.py`
8. Run `py pipeline/Movie_Recommendation_GMN_PL7_Offline_Evaluation.py`
9. Run `py pipeline/Movie_Recommendation_GMN_PL8_A_LogisticLikePredictor.py`

## Flask App Launch Command

- `py apps/Movie_Recommendation_GMN_HybridRouter.py`

## Matrix Matchmakers Hybrid Flow

The active hybrid UI uses the following sequence:

- `Choose Your Path`
- `Define Your Signal`
- `Choose Your Reality`
- `Follow the White Rabbit`
- `The System Has Chosen: Decoded Recommendations`

Reality naming:

- `Blue Pill`: Content Recommendation
- `Red Pill`: Collaborative Recommendation
- `Purple Pill`: Hybrid Recommendation

## Config And Dependencies

- `config.py` holds the main project constants and environment-driven overrides.
- `requirements.txt` contains the active runtime dependencies for the pipeline and Flask apps.

## Optional BERT Setup

If you want to run the semantic content-similarity experiment, install the repo dependencies and then run the BERT pipeline:

```powershell
py -m pip install -r requirements.txt
py pipeline/Movie_Recommendation_GMN_PL2_B_BERT_ContentSimilarity.py
```

This creates:

- `movie_content_similarity_bert_top20`

Use `sql/Movie_Recommendation_GMN_TFIDF_vs_BERT_SQL_Comparison.sql` to compare the BERT output against the main TF-IDF similarity table.

## Archived Material

Older or non-current artifacts are kept under `archive/` rather than being treated as part of the active project flow. That includes the retired content and collaborative interface files, plus the root-level BBA prototype scripts once their pipeline equivalents are in place.
