# GMN Recommendation Master Sheet

## Final Project Identity

- Project: `GMN Recommendation Pipeline`
- Hybrid app title: `Matrix Matchmakers`
- Final scope: enriched content recommender, collaborative KNN recommender, hybrid router, logistic like prediction

## Active Pipeline Files

1. `sql/Movie_Recommendation_GMN_PL1_SQL_Setup.sql`
2. `pipeline/Movie_Recommendation_GMN_PL0_Enrich.py`
3. `pipeline/Movie_Recommendation_GMN_PL2.py`
4. `pipeline/Movie_Recommendation_GMN_PL4.py`
5. `pipeline/Movie_Collaborative_Reco_BBA_PL4C.py`
6. `pipeline/Movie_Collaborative_Reco_BBA_PL4D_LeaveOneOut.py`
7. `pipeline/Movie_Recommendation_GMN_PL6_A_HybridRouter.py`
8. `pipeline/Movie_Recommendation_GMN_PL7_Offline_Evaluation.py`
9. `pipeline/Movie_Recommendation_GMN_PL8_A_LogisticLikePredictor.py`

## Active App Interface

- `apps/Movie_Recommendation_GMN_HybridRouter.py`

## Active App Support

- `apps/Movie_Recommendation_GMN_HybridRouter_Core.py`

## Active SQL Support Files

- `sql/Movie_Recommendation_GMN_PL4_SQL_Testing_Queries.sql`
- `sql/Movie_Collaborative_Reco_GMN_PL4C_SQL_Testing_Queries.sql`
- `sql/Movie_Collaborative_Reco_GMN_PL4D_LeaveOneOut_SQL_Testing_Queries.sql`
- `sql/Movie_Recommendation_GMN_PL5_A_SQL_Model_Comparison.sql`
- `sql/Movie_Recommendation_GMN_PL5_B_SQL_Model_Validation.sql`
- `sql/Movie_Recommendation_GMN_PL8_SQL_Final_Output_Queries.sql`

## Final Output Tables

### Content

- `movie_content_similarity_top20`
- `user_content_recommendations_top20`

### Collaborative

- `user_collaborative_knn_recommendations_top20`
- `collaborative_knn_leave_one_out_user_results`
- `collaborative_knn_leave_one_out_summary`

### Hybrid

- `user_hybrid_recommendations_top20`

### Evaluation

- `recommender_offline_eval_user_results`
- `recommender_offline_eval_summary`
- `user_hybrid_logistic_like_predictions_top20`
- `logistic_like_model_summary`

## Matrix Matchmakers UI Flow

1. `Choose Your Path`
2. `Define Your Signal`
3. `Choose Your Reality`
4. `Follow the White Rabbit`
5. `The System Has Chosen: Decoded Recommendations`

## User Scenario Framing

- `Active user`
  Use a user from the top-activity ranking in `Movie_Recommendation_GMN_PL5_B_SQL_Model_Validation.sql`.
- `Low-activity user`
  Use a user from the bottom-activity ranking in `Movie_Recommendation_GMN_PL5_B_SQL_Model_Validation.sql`.
- `Fallback user`
  Use a user from the fallback ranking or the documented edge case `userID = 442`.

Reference:

- `docs/Movie_Recommendation_GMN_User_442_Report.md`

## Launch Checklist

### Pipeline

1. Run SQL setup
2. Run enrichment
3. Run content similarity
4. Run content recommendations
5. Run collaborative recommendations
6. Run collaborative leave-one-out
7. Run hybrid router
8. Run offline evaluation
9. Run logistic like prediction

### App

1. Launch `Matrix Matchmakers` for the final hybrid experience

## Archive Rule

Files that are no longer part of the active system should live under `archive/` rather than being mixed into the current project flow.
