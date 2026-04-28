# GMN Recommendation Pipeline Report

## Report Purpose

This report summarizes the final active pipeline and explains how the repository is organized after cleanup.

## Active Components

### Enrichment And Content

- `Movie_Recommendation_GMN_PL0_Enrich.py`
- `Movie_Recommendation_GMN_PL2.py`
- `Movie_Recommendation_GMN_PL4.py`

This branch is responsible for enriched movie representation, item similarity, and user-level content recommendations.

### Collaborative

- `Movie_Collaborative_Reco_BBA_PL4C.py`
- `Movie_Collaborative_Reco_BBA_PL4D_LeaveOneOut.py`

This branch is responsible for collaborative KNN recommendation generation and collaborative validation.

### Hybrid

- `Movie_Recommendation_GMN_PL6_A_HybridRouter.py`

This branch is responsible for combining the two active recommenders into one final recommendation view.

### Evaluation

- `Movie_Recommendation_GMN_PL7_Offline_Evaluation.py`
- `Movie_Recommendation_GMN_PL8_A_LogisticLikePredictor.py`

These stages compare the active recommenders and then train the final logistic scoring layer.

## Active Outputs

### Modeling Outputs

- `movie_content_similarity_top20`
- `user_content_recommendations_top20`
- `user_collaborative_knn_recommendations_top20`
- `user_hybrid_recommendations_top20`

### Validation Outputs

- `collaborative_knn_leave_one_out_user_results`
- `collaborative_knn_leave_one_out_summary`
- `recommender_offline_eval_user_results`
- `recommender_offline_eval_summary`
- `user_hybrid_logistic_like_predictions_top20`
- `logistic_like_model_summary`

## Active App Layer

- `Movie_Recommendation_GMN_HybridRouter.py`
- `Movie_Recommendation_GMN_HybridRouter_Core.py`

The hybrid app is intentionally positioned as the only active presentation layer.

## Archived Material

Files that are no longer part of the active project story are stored under `archive/`. This keeps the repository cleaner while preserving older artifacts that may still be useful for reference.

## Final Repo Position

The repository should now be interpreted as a final hybrid recommender project with:

- one active content path
- one active collaborative path
- one active hybrid path
- one consistent documentation story
