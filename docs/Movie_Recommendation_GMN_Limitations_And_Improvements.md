# Limitations And Improvements

This document reflects the final simplified project state.

## Current Limitations

### 1. Content Quality Still Depends On Metadata Consistency

The content branch is stronger after TMDB enrichment, but recommendation quality still depends on how complete and clean the movie metadata is. Missing or inconsistent overviews, cast fields, or keywords can weaken similarity quality.

### 2. Collaborative Coverage Depends On Interaction Density

The collaborative KNN model performs best when the interaction matrix is dense enough to reveal stable co-preference patterns. Sparse users and less-rated movies can still receive weaker support.

### 3. The Hybrid Router Is Rule-Based

The hybrid branch currently uses a weighted blend plus an overlap bonus. That makes the system interpretable, but it is still hand-tuned rather than learned from evaluation targets.

The active final defaults are:

- content weight = `0.45`
- collaborative weight = `0.55`
- overlap bonus = `0.08`

### 4. Evaluation Scope Is Still Baseline-Level

The current offline evaluation is useful for model comparison, but it is still a baseline framework. It does not yet represent a broader production-grade experimentation setup with richer ranking metrics, calibration checks, or business-level constraints.

### 5. UI And Pipeline Are More Centralized, But Config Is Still Split

The repository is cleaner now and the final interface is centralized around one hybrid app, but some constants still live locally inside scripts rather than being fully driven from one shared configuration layer.

## Near-Term Improvements

### 1. Move More Runtime Settings Into Shared Config

Centralize values such as:

- database path
- default recommendation depth
- app-level runtime toggles
- model weighting defaults

This would reduce duplication and make the active repo easier to operate.

### 2. Tune Hybrid Weights With Evaluation Tables

Use the offline evaluation results to tune:

- content weight
- collaborative weight
- overlap bonus

instead of relying only on manual defaults.

### 3. Improve Enrichment Retry And Coverage

The enrichment stage should retry missing or failed rows so the enriched feature layer becomes more complete and stable across the catalog.

### 4. Add More Content Feature Controls

The content model could improve further by:

- deduplicating repeated text fragments
- trimming generic metadata tokens
- weighting stronger fields more deliberately
- testing alternate text-composition strategies

### 5. Extend Collaborative Modeling

The collaborative branch could be expanded with:

- user-user baselines
- matrix factorization
- implicit-feedback methods
- stronger neighborhood tuning

## Longer-Term Improvements

### 1. Learn The Hybrid Router

The next major upgrade would be a learned reranker or confidence-based router that decides when to trust:

- content
- collaborative
- agreement between both

### 2. Strengthen Evaluation Breadth

Future evaluation could add:

- NDCG or MAP-style ranking metrics
- segment-level comparisons
- cold-start analysis
- UI-level qualitative review

### 3. Create A Fully Unified App Configuration Layer

The final Flask interface now tells a much cleaner story, but a dedicated shared configuration pattern would make app branding, DB settings, and launch behavior easier to maintain over time.
