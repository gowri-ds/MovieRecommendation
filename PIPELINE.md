# GMN Recommendation Pipeline

## End-to-End Flow

This project follows a staged recommendation pipeline. Each stage builds on the output of the previous one and writes a new SQLite table that can be reused later.

### Step 1: Prepare Movie Features

The system starts from the movie feature layer in the database, mainly:

- `movie_content_clean`
- `vw_movie_content_features`

Supporting SQL assets for this stage live in the `sql/` folder. In particular:

- [Movie_Content_Reco_GMN_PL1_SQL_Setup.sql](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/sql/Movie_Content_Reco_GMN_PL1_SQL_Setup.sql) supports the base SQL preparation layer.

These sources contain the movie metadata used for recommendation, such as:

- movie IDs and titles,
- genre fields,
- combined text features,
- links and display metadata for the UI.

### Step 2: Build Movie-to-Movie Similarity

There are two parallel movie similarity models:

#### TF-IDF path

[Movie_Content_Reco_GMN_PL2.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/Movie_Content_Reco_GMN_PL2.py) reads `combined_text`, converts it into TF-IDF vectors, computes cosine similarity, and stores the top 20 similar movies for each movie in:

- `movie_content_similarity_top20`

#### Genre OHE path

[Movie_Content_Reco_GMN_PL2B_Genre_OHE.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/Movie_Content_Reco_GMN_PL2B_Genre_OHE.py) reads movie genres, converts them into one-hot encoded vectors, computes cosine similarity, and stores the top 20 similar movies for each movie in:

- `movie_genre_ohe_similarity_top20`

At this point, the project has two different ways to describe movie similarity:

- a richer text-based TF-IDF similarity,
- a simpler but more interpretable genre-based similarity.

### Step 3: Turn Similar Movies into User Recommendations

The next layer moves from item similarity to user recommendation.

#### TF-IDF user recommendations

[Movie_Content_Reco_GMN_PL4.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/Movie_Content_Reco_GMN_PL4.py) does the following:

1. Reads user ratings from `user_movie_interactions`.
2. Treats ratings `>= 4.0` as liked movies.
3. Looks up similar movies for each liked movie using `movie_content_similarity_top20`.
4. Removes movies the user has already seen or rated.
5. Aggregates similarity support across multiple liked movies.
6. Ranks the top 20 recommendations per user.

It saves the result to:

- `user_content_recommendations_top20`

#### Genre OHE user recommendations

[Movie_Content_Reco_GMN_PL4B_Genre_OHE.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/Movie_Content_Reco_GMN_PL4B_Genre_OHE.py) repeats the same process, but uses the genre-based similarity table instead. It saves the result to:

- `user_content_recommendations_genre_ohe_top20`

At this stage, each user now has two recommendation lists:

- one from TF-IDF,
- one from Genre OHE.

### Step 4: Combine the Two Recommendation Models

The project then adds a router layer that combines the two user-level recommendation lists.

#### Weighted Hybrid Router

[Movie_Content_Reco_GMN_PL6_A_HybridRouter.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/Movie_Content_Reco_GMN_PL6_A_HybridRouter.py) normalizes the TF-IDF and OHE recommendation scores, merges the two result sets, and computes:

- a weighted blend of both models,
- plus a small bonus when both models recommend the same movie.

It saves the combined output to:

- `user_hybrid_recommendations_top20`

#### Confidence-Based Hybrid Router

[Movie_Content_Reco_GMN_PL6_B_ConfidenceRouter.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/Movie_Content_Reco_GMN_PL6_B_ConfidenceRouter.py) takes the hybrid idea one step further.

Instead of using one fixed formula for every movie, it:

1. normalizes TF-IDF and OHE scores,
2. checks how strong the TF-IDF signal is,
3. assigns each recommendation to a confidence bucket,
4. changes the score weights based on that bucket,
5. adds a bonus if both models agree.

It saves the final routed output to:

- `user_confidence_hybrid_recommendations_top20`

This is the most adaptive recommendation table in the project.

### Step 5: Evaluate the Models

[Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py) evaluates all four approaches:

- TF-IDF model,
- Genre OHE model,
- Weighted Hybrid Router,
- Confidence Hybrid Router.

It uses a leave-one-out offline test:

1. identify liked movies with ratings `>= 4.0`,
2. require at least 5 liked movies per user,
3. hold out one liked movie per eligible user,
4. rebuild recommendations from the remaining liked movies,
5. check whether the held-out movie appears in the top 10.

It writes:

- `recommender_offline_eval_user_results`
- `recommender_offline_eval_summary`

This stage tells you which recommender performed best.

### Step 5B: Compare, Validate, and Inspect Outputs

The repo also includes SQL helper files that support testing, comparison, and presentation of results:

- [Movie_Content_Reco_GMN_PL4_SQL_Testing_Queries.sql](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/sql/Movie_Content_Reco_GMN_PL4_SQL_Testing_Queries.sql): testing and inspection queries
- [Movie_Content_Reco_GMN_PL5_A_SQL_Model_Comparison.sql](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/sql/Movie_Content_Reco_GMN_PL5_A_SQL_Model_Comparison.sql): comparison queries across movie and user model outputs
- [Movie_Content_Reco_GMN_PL5_B_SQL_Model_Validation.sql](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/sql/Movie_Content_Reco_GMN_PL5_B_SQL_Model_Validation.sql): validation queries for comparison tables
- [Movie_Content_Reco_GMN_PL8_SQL_Final_Output_Queries.sql](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/sql/Movie_Content_Reco_GMN_PL8_SQL_Final_Output_Queries.sql): final reporting and output queries

### Step 6: Present Results in the Web App

The recommendation outputs are then surfaced in the Flask apps:

- [GMN_Purple_Lilac_Content_Based_Reco.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/GMN_Purple_Lilac_Content_Based_Reco.py)
- [matrixmatchmakers_contentbasedreco.py](/c:/Users/ngowr/Coding%20Projects/GMN_Content_Reco/matrixmatchmakers_contentbasedreco.py)

These apps let you:

- choose a recommendation model,
- enter a user ID,
- retrieve recommendations,
- browse similar movies,
- view poster images and metadata.

## Short Version

The project pipeline can be summarized like this:

1. Build movie features.
2. Build TF-IDF similarity table.
3. Build Genre OHE similarity table.
4. Build TF-IDF user recommendations.
5. Build Genre OHE user recommendations.
6. Build weighted hybrid recommendations.
7. Build confidence-based hybrid recommendations.
8. Evaluate all methods offline.
9. Run SQL testing, comparison, and final output queries as needed.
10. Display results in Flask UI apps.

## File Order To Run

If you want to rebuild the project from scratch, the scripts should generally run in this order:

1. `Movie_Content_Reco_GMN_PL2.py`
2. `Movie_Content_Reco_GMN_PL2B_Genre_OHE.py`
3. `Movie_Content_Reco_GMN_PL4.py`
4. `Movie_Content_Reco_GMN_PL4B_Genre_OHE.py`
5. `Movie_Content_Reco_GMN_PL6_A_HybridRouter.py`
6. `Movie_Content_Reco_GMN_PL6_B_ConfidenceRouter.py`
7. `Movie_Content_Reco_GMN_PL7_Offline_Evaluation.py`

The Flask apps are used after the tables are already built.

Optional SQL support files can be used alongside the pipeline:

1. `sql/Movie_Content_Reco_GMN_PL1_SQL_Setup.sql`
2. `sql/Movie_Content_Reco_GMN_PL4_SQL_Testing_Queries.sql`
3. `sql/Movie_Content_Reco_GMN_PL5_A_SQL_Model_Comparison.sql`
4. `sql/Movie_Content_Reco_GMN_PL5_B_SQL_Model_Validation.sql`
5. `sql/Movie_Content_Reco_GMN_PL8_SQL_Final_Output_Queries.sql`

## Why This Structure Works

This staged design is useful because:

- each script has one clear job,
- each output is saved to SQLite for reuse,
- the models can be compared side by side,
- the routers can be tested independently,
- the UI can query finished tables instead of rebuilding recommendations live.
