# GMN Content Recommendation Pipeline

This project builds and compares several content-based movie recommendation approaches on top of a SQLite database. It includes item similarity models, user-level recommenders, hybrid routing strategies, offline evaluation, SQL support files, and two Flask UI apps.

## Project Scope

Core workflows:

- TF-IDF movie similarity and user recommendation
- Genre OHE movie similarity and user recommendation
- Weighted hybrid router
- Confidence-based hybrid router
- Offline evaluation
- Flask apps for recommendation and similarity lookup

Database used:

- `G:/My Drive/BSAN 780 Analytics Capstone/Final Project/Movies.db`

## Repo Structure

Pipeline scripts:

- `pipeline/Movie_Content_Reco_GMN_PL2.py`
- `pipeline/Movie_Content_Reco_GMN_PL2B_Genre_OHE.py`
- `pipeline/Movie_Content_Reco_GMN_PL4.py`
- `pipeline/Movie_Content_Reco_GMN_PL4B_Genre_OHE.py`
- `pipeline/Movie_Content_Reco_GMN_PL6_A_HybridRouter.py`
- `pipeline/Movie_Content_Reco_GMN_PL6_B_ConfidenceRouter.py`
- `pipeline/Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py`

Apps:

- `apps/Movie_Content_Reco_GMN_App_Purple_Lilac.py`
- `apps/Movie_Content_Reco_GMN_App_Matrix.py`
- `apps/Movie_Content_Reco_GMN_App.py`

Docs:

- `docs/Movie_Content_Reco_GMN_Pipeline.md`
- `docs/Movie_Content_Reco_GMN_Project_Report.md`
- `docs/Movie_Content_Reco_GMN_Limitations_And_Improvements.md`

SQL:

- `sql/Movie_Content_Reco_GMN_PL1_SQL_Setup.sql`
- `sql/Movie_Content_Reco_GMN_PL4_SQL_Testing_Queries.sql`
- `sql/Movie_Content_Reco_GMN_PL5_A_SQL_Model_Comparison.sql`
- `sql/Movie_Content_Reco_GMN_PL5_B_SQL_Model_Validation.sql`
- `sql/Movie_Content_Reco_GMN_PL8_SQL_Final_Output_Queries.sql`

Frontend assets:

- `templates/`
- `static/`

## Main Output Tables

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

## How To Run

Install dependencies:

```bash
py -m pip install -r requirements.txt
```

Run the pipeline in this order:

1. `py pipeline/Movie_Content_Reco_GMN_PL2.py`
2. `py pipeline/Movie_Content_Reco_GMN_PL2B_Genre_OHE.py`
3. `py pipeline/Movie_Content_Reco_GMN_PL4.py`
4. `py pipeline/Movie_Content_Reco_GMN_PL4B_Genre_OHE.py`
5. `py pipeline/Movie_Content_Reco_GMN_PL6_A_HybridRouter.py`
6. `py pipeline/Movie_Content_Reco_GMN_PL6_B_ConfidenceRouter.py`
7. `py pipeline/Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py`

Run the apps:

```bash
py apps/Movie_Content_Reco_GMN_App_Purple_Lilac.py
py apps/Movie_Content_Reco_GMN_App_Matrix.py
```

Then open:

- `http://127.0.0.1:5000`

## Evaluation Snapshot

Latest offline evaluation summary:

- eligible users: `603`
- `genre_ohe_model`: hit rate@10 = `0.0100`
- `confidence_hybrid_router`: hit rate@10 = `0.0083`
- `tfidf_model`: hit rate@10 = `0.0050`
- `weighted_hybrid_router`: hit rate@10 = `0.0033`

Quick interpretation:

- Genre OHE performed best on this leave-one-out test.
- The confidence hybrid router outperformed the weighted hybrid router.
- Overall hit rates are low, so the system is functional but still limited in predictive accuracy.

## Further Documentation

For deeper detail, see:

- [Pipeline Walkthrough](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/docs/Movie_Content_Reco_GMN_Pipeline.md)
- [Project Report](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/docs/Movie_Content_Reco_GMN_Project_Report.md)
- [Evaluation, Limitations, and Improvements](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/docs/Movie_Content_Reco_GMN_Limitations_And_Improvements.md)
