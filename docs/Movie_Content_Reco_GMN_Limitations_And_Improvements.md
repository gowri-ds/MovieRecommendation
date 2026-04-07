# GMN Evaluation, Limitations, and Future Improvements

## Evaluation Results

The offline evaluation compared four approaches using a leave-one-out design over `603` eligible users. A liked movie was defined as a rating `>= 4.0`, users needed at least `5` liked movies to be included, and one liked movie per user was held out. A model was counted as a hit if the held-out movie appeared in the top `10` recommendations.

Latest summary:

- `genre_ohe_model`: `6` hits, `hit_rate@10 = 0.0100`
- `confidence_hybrid_router`: `5` hits, `hit_rate@10 = 0.0083`
- `tfidf_model`: `3` hits, `hit_rate@10 = 0.0050`
- `weighted_hybrid_router`: `2` hits, `hit_rate@10 = 0.0033`

Supporting ranking metrics:

- `genre_ohe_model`: `mrr_at_k = 0.0037`, `ndcg_at_k = 0.0052`
- `confidence_hybrid_router`: `mrr_at_k = 0.0021`, `ndcg_at_k = 0.0036`
- `tfidf_model`: `mrr_at_k = 0.0035`, `ndcg_at_k = 0.0038`
- `weighted_hybrid_router`: `mrr_at_k = 0.0033`, `ndcg_at_k = 0.0033`

## Interpretation

These results show that:

- the Genre OHE model performed best overall on this offline test,
- the confidence-based hybrid router was the strongest hybrid method,
- the confidence router improved over the fixed weighted hybrid router,
- the TF-IDF model alone underperformed the simpler Genre OHE baseline,
- all methods produced low absolute hit rates, so the system is operational but still limited in predictive accuracy.

The evaluation pipeline itself is working correctly because it produced valid user-level and summary-level outputs, compared all four models consistently, and generated nonzero hit counts across the tested methods.

## Current Limitations

### 1. Content-Based Only Design

The project uses only content-based recommendation. It does not use collaborative filtering, matrix factorization, or user-to-user similarity. Because of this, the system may miss important taste patterns that are visible in collective user behavior.

### 2. Limited Feature Representation

The TF-IDF path depends heavily on the quality of `combined_text`. If the text fields are noisy, repetitive, sparse, or not semantically rich, similarity quality drops. The model may over-weight repeated names, keywords, or metadata artifacts instead of true thematic similarity.

### 3. Genre OHE Is Coarse

The Genre OHE approach is simple and interpretable, but it only captures broad genre overlap. It cannot distinguish between movies that share the same genres but differ greatly in tone, style, pacing, or narrative structure.

### 4. Small Candidate Pool

The current pipeline builds from Top-20 movie similarity tables. This limits the downstream recommendation pool. A relevant movie may never be considered if it does not appear in the top 20 similar movies for the user’s liked titles.

### 5. Simple User Preference Modeling

The user recommendation stage treats ratings `>= 4.0` as liked movies and aggregates recommendation support by summing similarity scores. This does not fully capture:

- stronger preference for `5.0` versus `4.0`,
- recency effects,
- varying confidence in different user interactions.

### 6. Hand-Tuned Hybrid Parameters

The weighted hybrid and confidence hybrid both rely on manually chosen thresholds, bonuses, and weights. These settings are reasonable, but they are not yet optimized through systematic tuning against evaluation results.

### 7. Low Offline Accuracy

Even the best-performing model produced only `6` hits out of `603` users. This indicates that the recommender system is functioning structurally, but its predictive strength remains limited in the current form.

## Future Improvements

### 1. Improve the Movie Feature Layer

Strengthen the text and metadata used by the TF-IDF model by:

- improving `combined_text`,
- adding plot summaries, keywords, cast, director, and writer fields,
- removing duplicated or noisy tokens,
- weighting important fields differently.

This would likely improve the semantic quality of the TF-IDF similarity model.

### 2. Expand Candidate Generation

Increase the movie-to-movie similarity output from Top-20 to Top-50 or Top-100. This would allow the user-level recommendation stage to consider a larger candidate pool and could improve the chance of recovering the held-out movie.

### 3. Improve User Preference Modeling

Build a stronger user profile by:

- weighting higher ratings more strongly,
- considering recent interactions,
- using more advanced aggregation than raw score summation,
- requiring stronger multi-movie support for candidates.

This could produce more personalized and more stable recommendation rankings.

### 4. Tune Hybrid Router Parameters

Use the offline evaluation framework to systematically test:

- TF-IDF and OHE weight combinations,
- confidence thresholds,
- overlap bonus values,
- fallback penalties.

This would make the hybrid routing logic more data-driven instead of manually tuned.

### 5. Add Better Reranking Features

Once candidates are generated, the system could rerank them using:

- number of supporting liked movies,
- average supporting rating,
- popularity smoothing,
- diversity or novelty adjustments.

This could improve recommendation ordering even if the candidate set stays the same.

### 6. Replace or Extend TF-IDF with Embeddings

Instead of relying only on TF-IDF, the project could use embedding-based representations for movie descriptions or metadata. Embeddings may better capture semantic similarity and improve performance beyond simple keyword overlap.

### 7. Add Collaborative Filtering

The biggest long-term improvement would be to combine content-based methods with collaborative filtering. A hybrid system that uses both item features and user behavior would likely outperform the current content-only design.

## Recommended Next Step

If the goal is to improve results without fully redesigning the project, the most practical next steps are:

1. improve `combined_text` and movie metadata quality,
2. expand the similarity candidate pool beyond top 20,
3. tune the confidence-router thresholds and weights using the evaluation script,
4. weight user likes by rating strength rather than using a single binary threshold.

These changes would preserve the current architecture while giving the recommendation system a better chance of improving hit rate.
