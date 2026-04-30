# GMN Recommendation Project Report

## Project Goal

The final GMN project is a simplified movie recommender built on SQLite. The goal is to compare and combine four active approaches:

- a TMDB-enriched content model
- a collaborative KNN model
- a hybrid router that merges both
- a logistic like-prediction layer for final recommendation scoring

The final user-facing hybrid app is presented as `Matrix Matchmakers`.

## Final System Design

The repository intentionally avoids multiple competing content and hybrid branches. Instead, it keeps one active path for each major idea:

- one content branch
- one collaborative branch
- one hybrid branch
- one final supervised scoring branch

This makes the project easier to explain, easier to run, and easier to evaluate.

## Data And Feature Layer

The system starts with a base SQL layer that standardizes movie and interaction data into reusable tables and views. That layer supports both modeling families.

The enrichment stage then extends the movie metadata with TMDB-derived fields such as:

- overview
- keywords
- director
- cast
- release context when available

The enriched content view becomes the preferred text source for downstream similarity and recommendation generation.

## Content Recommendation Branch

The content branch uses enriched `combined_text` features to build TF-IDF movie similarity. That similarity table is then converted into user-level recommendations by combining item similarity with user interaction history.

Main outputs:

- `movie_content_similarity_top20`
- `user_content_recommendations_top20`

## Collaborative Recommendation Branch

The collaborative branch uses user behavior directly through a user-user KNN approach with mean-centered ratings and cosine similarity. This branch is especially useful where similar-user behavior reveals relationships that do not appear in metadata alone.

Main outputs:

- `user_collaborative_knn_recommendations_top20`
- `collaborative_knn_leave_one_out_user_results`
- `collaborative_knn_leave_one_out_summary`

## Hybrid Recommendation Branch

The hybrid router combines the content and collaborative tables into one ranked output. The current implementation blends:

- normalized content score
- normalized collaborative score
- an overlap bonus when both models recommend the same movie

The active fixed settings in the final pipeline are:

- content weight = `0.45`
- collaborative weight = `0.55`
- overlap bonus = `0.08`

Main output:

- `user_hybrid_recommendations_top20`

## Logistic Like Prediction Layer

The logistic layer takes hybrid candidates and estimates the probability that a user will positively rate each recommendation. This adds a supervised interpretation on top of the hybrid ranking without replacing the earlier pipeline steps.

Main outputs:

- `user_hybrid_logistic_like_predictions_top20`
- `logistic_like_model_summary`

## Evaluation Layer

The final evaluation stage compares the three active recommendation outputs:

- `content_model`
- `collaborative_knn_model`
- `hybrid_router`

It writes both per-user and summary-level evaluation tables, which support tuning and interpretation of the simplified final system before the logistic layer is applied.

## App Layer

The project now exposes one final Flask interface: the hybrid app `Matrix Matchmakers`.

It is supported by a shared hybrid app core module and frames the recommendation flow as:

- define the signal
- choose the reality
- follow the white rabbit
- reveal decoded recommendations

## User Scenarios

The final hybrid interface is easiest to explain through three user scenarios:

- `Active user`
  A user with a strong interaction history and enough signal for normal personalized recommendations.
- `Low-activity user`
  A user with limited interaction history, where personalization is weaker and recommendation confidence is lower.
- `Fallback user`
  A user who may have interaction rows but still receives no generated recommendation rows from the prebuilt content, collaborative, or hybrid tables.

These scenarios help explain why the router needs more than one response pattern. The app is not only ranking movies, it is also deciding how to respond when the available user signal is strong, weak, or unusable.

The clearest fallback example in this project is `userID = 442`, which has interaction data but no rows in any of the three recommendation output tables. That case is documented separately in:

- `docs/Movie_Recommendation_GMN_User_442_Report.md`

## Why This Version Matters

This final version is stronger than the earlier multi-branch layout because it:

- removes duplicate or competing model paths
- focuses evaluation on the actual final recommenders
- keeps the codebase more maintainable
- aligns the documentation and UI with the active project scope
- supports a final probability-based output for presentation and downstream use

## Final Takeaway

The GMN repository now represents a coherent hybrid recommendation baseline:

- richer content signals through enrichment
- collaborative signals from behavior
- a single hybrid layer for ranking
- a final logistic layer for interpretable like probability

That makes it a good academic capstone delivery and a practical base for future tuning work.
