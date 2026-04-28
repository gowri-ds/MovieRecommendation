# GMN Recommendation Pipeline Report

This report summarizes the simplified active pipeline in the repository.

## Active Scripts

- [Movie_Content_Reco_GMN_PL0_Enrich.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Content_Reco_GMN_PL0_Enrich.py)
- [Movie_Content_Reco_GMN_PL2.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Content_Reco_GMN_PL2.py)
- [Movie_Content_Reco_GMN_PL4.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Content_Reco_GMN_PL4.py)
- [Movie_Collaborative_Reco_GMN_PL4C.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Collaborative_Reco_GMN_PL4C.py)
- [Movie_Collaborative_Reco_GMN_PL4D_LeaveOneOut.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Collaborative_Reco_GMN_PL4D_LeaveOneOut.py)
- [Movie_Content_Reco_GMN_PL6_A_HybridRouter.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Content_Reco_GMN_PL6_A_HybridRouter.py)
- [Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py)

## Content Branch

The content branch now centers on TMDB enrichment plus one main similarity/recommendation path:

- TMDB metadata is stored in `movie_metadata_enriched`
- the enriched feature view is `vw_movie_content_features_enriched`
- movie-level similarity is stored in `movie_content_similarity_top20`
- user-level content recommendations are stored in `user_content_recommendations_top20`

## Collaborative Branch

The collaborative branch uses item-item KNN and stores:

- `user_collaborative_knn_recommendations_top20`

It also includes leave-one-out tuning outputs:

- `collaborative_knn_leave_one_out_user_results`
- `collaborative_knn_leave_one_out_summary`

## Hybrid Branch

The hybrid branch now combines only:

- the enriched content recommendation table
- the collaborative recommendation table

Its output is:

- `user_hybrid_recommendations_top20`

## Evaluation

The offline evaluation step now compares:

- `content_model`
- `collaborative_knn_model`
- `hybrid_router`

and writes:

- `recommender_offline_eval_user_results`
- `recommender_offline_eval_summary`

## Removed Branches

Older parallel branches were removed so the repo keeps one main content path, one collaborative path, and one hybrid path.
