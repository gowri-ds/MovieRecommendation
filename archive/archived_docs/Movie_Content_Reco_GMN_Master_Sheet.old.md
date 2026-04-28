# GMN Recommendation Master Sheet

This master sheet tracks the simplified final pipeline used in the repository.

## Final Pipeline

1. [Movie_Content_Reco_GMN_PL1_SQL_Setup.sql](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/sql/Movie_Content_Reco_GMN_PL1_SQL_Setup.sql)
2. [Movie_Content_Reco_GMN_PL0_Enrich.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Content_Reco_GMN_PL0_Enrich.py)
3. [Movie_Content_Reco_GMN_PL2.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Content_Reco_GMN_PL2.py)
4. [Movie_Content_Reco_GMN_PL4.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Content_Reco_GMN_PL4.py)
5. [Movie_Collaborative_Reco_GMN_PL4C.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Collaborative_Reco_GMN_PL4C.py)
6. [Movie_Collaborative_Reco_GMN_PL4D_LeaveOneOut.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Collaborative_Reco_GMN_PL4D_LeaveOneOut.py)
7. [Movie_Content_Reco_GMN_PL6_A_HybridRouter.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Content_Reco_GMN_PL6_A_HybridRouter.py)
8. [Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/pipeline/Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py)

## Final Output Tables

- `movie_metadata_enriched`
- `vw_movie_content_features_enriched`
- `movie_content_similarity_top20`
- `user_content_recommendations_top20`
- `user_collaborative_knn_recommendations_top20`
- `user_hybrid_recommendations_top20`
- `collaborative_knn_leave_one_out_user_results`
- `collaborative_knn_leave_one_out_summary`
- `recommender_offline_eval_user_results`
- `recommender_offline_eval_summary`

## Notes

- Older duplicate branches were removed from the active repo flow.
- The apps and SQL helper files have been updated to reflect this simplified structure.

## One-Page Run Checklist

Use this checklist when you want the final outputs to appear correctly in the apps.

### Step 1: Run SQL setup

Run:

`sql/Movie_Content_Reco_GMN_PL1_SQL_Setup.sql`

This creates:

- `movie_content_clean`
- `user_movie_interactions`
- `vw_movie_content_features`

### Step 2: Run Python pipeline in order

Run these in this exact order:

1. `py pipeline/Movie_Content_Reco_GMN_PL0_Enrich.py`
2. `py pipeline/Movie_Content_Reco_GMN_PL2.py`
3. `py pipeline/Movie_Content_Reco_GMN_PL4.py`
4. `py pipeline/Movie_Collaborative_Reco_GMN_PL4C.py`
5. `py pipeline/Movie_Collaborative_Reco_GMN_PL4D_LeaveOneOut.py`
6. `py pipeline/Movie_Content_Reco_GMN_PL6_A_HybridRouter.py`
7. `py pipeline/Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py`

### Step 3: Final tables you should have

Before opening the apps, confirm these outputs exist:

- `movie_metadata_enriched`
- `vw_movie_content_features_enriched`
- `movie_content_similarity_top20`
- `user_content_recommendations_top20`
- `user_collaborative_knn_recommendations_top20`
- `user_hybrid_recommendations_top20`
- `recommender_offline_eval_summary`

### Step 4: Launch the apps

Content app:

`py apps/Movie_Content_Reco_GMN_App_Purple_Lilac.py`

Collaborative app:

`py apps/Movie_Content_Reco_GMN_App_Matrix.py`

Combined app with content, collaborative, and hybrid filters:

`py apps/Movie_Content_Reco_GMN_App.py`

### Important note

If `PL0_Enrich.py` is already running, do not start it again. Let it finish, then continue with `PL2.py`.
