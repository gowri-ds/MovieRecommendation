# GMN Recommendation Master Sheet

This master sheet reflects the simplified final pipeline used in the repository.

## Final Run Order

1. Run [Movie_Content_Reco_GMN_PL1_SQL_Setup.sql](../sql/Movie_Content_Reco_GMN_PL1_SQL_Setup.sql)
2. Run [Movie_Content_Reco_GMN_PL0_Enrich.py](../pipeline/Movie_Content_Reco_GMN_PL0_Enrich.py)
3. Run [Movie_Content_Reco_GMN_PL2.py](../pipeline/Movie_Content_Reco_GMN_PL2.py)
4. Run [Movie_Content_Reco_GMN_PL4.py](../pipeline/Movie_Content_Reco_GMN_PL4.py)
5. Run [Movie_Collaborative_Reco_GMN_PL4C.py](../pipeline/Movie_Collaborative_Reco_GMN_PL4C.py)
6. Run [Movie_Collaborative_Reco_GMN_PL4D_LeaveOneOut.py](../pipeline/Movie_Collaborative_Reco_GMN_PL4D_LeaveOneOut.py)
7. Run [Movie_Content_Reco_GMN_PL6_A_HybridRouter.py](../pipeline/Movie_Content_Reco_GMN_PL6_A_HybridRouter.py)
8. Run [Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py](../pipeline/Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py)

## What Each Step Produces

- `PL1 SQL Setup`
  Creates the base cleaned layer:
  `movie_content_clean`, `user_movie_interactions`, `vw_movie_content_features`

- `PL0 Enrich`
  Creates:
  `movie_metadata_enriched`, `vw_movie_content_features_enriched`

- `PL2`
  Creates:
  `movie_content_similarity_top20`

- `PL4`
  Creates:
  `user_content_recommendations_top20`

- `PL4C`
  Creates:
  `user_collaborative_knn_recommendations_top20`

- `PL4D`
  Creates:
  `collaborative_knn_leave_one_out_user_results`,
  `collaborative_knn_leave_one_out_summary`

- `PL6_A`
  Creates:
  `user_hybrid_recommendations_top20`

- `PL7`
  Creates:
  `recommender_offline_eval_user_results`,
  `recommender_offline_eval_summary`

## App Run Options

- Content app:
  `py apps/Movie_Content_Reco_GMN_App_Purple_Lilac.py`

- Collaborative app:
  `py apps/Movie_Content_Reco_GMN_App_Matrix.py`

- Combined app with content, collaborative, and hybrid filters:
  `py apps/Movie_Content_Reco_GMN_App.py`
