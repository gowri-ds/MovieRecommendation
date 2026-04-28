# GMN Pipeline Walkthrough

This document describes the active final pipeline in the repository.

## Step 1: Base SQL Setup

File:

- [Movie_Recommendation_GMN_PL1_SQL_Setup.sql](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/sql/Movie_Recommendation_GMN_PL1_SQL_Setup.sql)

Purpose:

- create the reusable movie and interaction layer
- prepare the base content feature view

Key outputs:

- `movie_content_clean`
- `user_movie_interactions`
- `vw_movie_content_features`

## Step 2: TMDB Enrichment

File:

- [Movie_Recommendation_GMN_PL0_Enrich.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Recommendation_GMN_PL0_Enrich.py)

Purpose:

- enrich movies with external metadata
- build the preferred enriched content feature view

Key outputs:

- `movie_metadata_enriched`
- `vw_movie_content_features_enriched`

## Step 3: Content Similarity

File:

- [Movie_Recommendation_GMN_PL2.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Recommendation_GMN_PL2.py)

Purpose:

- vectorize enriched movie text
- compute content similarity between movies

Key output:

- `movie_content_similarity_top20`

## Step 4: User-Level Content Recommendations

File:

- [Movie_Recommendation_GMN_PL4.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Recommendation_GMN_PL4.py)

Purpose:

- transform content similarity into user-level recommendations

Key output:

- `user_content_recommendations_top20`

## Step 5: Collaborative Recommendations

Files:

- [Movie_Collaborative_Reco_BBA_PL4C.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Collaborative_Reco_BBA_PL4C.py)
- [Movie_Collaborative_Reco_BBA_PL4D_LeaveOneOut.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Collaborative_Reco_BBA_PL4D_LeaveOneOut.py)

Purpose:

- generate item-item collaborative recommendations
- validate collaborative performance using leave-one-out evaluation

Key outputs:

- `user_collaborative_knn_recommendations_top20`
- `collaborative_knn_leave_one_out_user_results`
- `collaborative_knn_leave_one_out_summary`

## Step 6: Hybrid Routing

File:

- [Movie_Recommendation_GMN_PL6_A_HybridRouter.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Recommendation_GMN_PL6_A_HybridRouter.py)

Purpose:

- merge the content and collaborative user recommendation tables
- score overlap and produce one final hybrid ranking

Key output:

- `user_hybrid_recommendations_top20`

## Step 7: Offline Evaluation

File:

- [Movie_Recommendation_GMN_PL7_Offline_Evaluation.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Recommendation_GMN_PL7_Offline_Evaluation.py)

Purpose:

- compare the active content, collaborative, and hybrid outputs

Key outputs:

- `recommender_offline_eval_user_results`
- `recommender_offline_eval_summary`

## Pipeline Run Order

1. `sql/Movie_Recommendation_GMN_PL1_SQL_Setup.sql`
2. `py pipeline/Movie_Recommendation_GMN_PL0_Enrich.py`
3. `py pipeline/Movie_Recommendation_GMN_PL2.py`
4. `py pipeline/Movie_Recommendation_GMN_PL4.py`
5. `py pipeline/Movie_Collaborative_Reco_BBA_PL4C.py`
6. `py pipeline/Movie_Collaborative_Reco_BBA_PL4D_LeaveOneOut.py`
7. `py pipeline/Movie_Recommendation_GMN_PL6_A_HybridRouter.py`
8. `py pipeline/Movie_Recommendation_GMN_PL7_Offline_Evaluation.py`
9. `py pipeline/Movie_Recommendation_GMN_PL8_A_LogisticLikePredictor.py`

## App Layer Alignment

The pipeline is surfaced through one active interface:

- Matrix Matchmakers hybrid app

The hybrid app is aligned with the final hybrid table and should be treated as the main integrated interface for the finished project. Shared UI logic lives in `apps/Movie_Recommendation_GMN_HybridRouter_Core.py`.
