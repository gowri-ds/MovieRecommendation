# Hybrid Recommendation Strategy Comparison

## Purpose

This document compares the main hybrid recommendation strategies that could be used in the GMN project. It is intended to support team discussion before deciding whether to keep the current weighted router or move to a more advanced design.

## Current Project Position

The current GMN hybrid router uses a weighted combination of:

- content recommendation score
- collaborative recommendation score
- overlap bonus when both models recommend the same movie

The active fixed weights in the final pipeline are:

- content weight = `0.45`
- collaborative weight = `0.55`
- overlap bonus = `0.08`

This is a valid and explainable baseline. The question is whether the team wants to keep that approach, refine it, or replace it with a more adaptive or learned strategy.

## Strategy Comparison

### 1. Fixed Weighted Hybrid

#### How it works

The final score is computed from fixed weights such as:

- content weight
- collaborative weight
- overlap bonus

The same formula is used for every user.

#### Strengths

- easiest to implement
- easiest to explain
- highly transparent
- strong baseline for a capstone

#### Weaknesses

- weights are manually chosen unless separately tuned
- same blend is used for all users, even when user history differs
- less flexible for cold-start or sparse-user cases

#### Best use case

- when the team wants a simple, defendable hybrid baseline
- when presentation clarity matters more than modeling complexity

#### Fit for GMN

Very high. This is already close to the current project design.

## 2. Validation-Tuned Weighted Hybrid

### How it works

The structure remains the same as the fixed weighted hybrid, but the actual weights are selected using offline comparison and validation results instead of manual guesses.

### Strengths

- still simple and explainable
- stronger academic justification than hard-coded defaults
- improves credibility of the hybrid design

### Weaknesses

- still uses one global blend for all users
- does not adapt to different user profiles

### Best use case

- when the team wants to improve the current router without changing the overall architecture

### Fit for GMN

Excellent. This is probably the cleanest next step if the team wants minimal disruption.

## 3. Rule-Based or Switching Hybrid

### How it works

The system chooses which recommendation path to use based on simple rules, for example:

- new user -> fallback or content
- low-activity user -> content-heavy
- active user -> collaborative or hybrid
- no generated rows -> top-rated fallback

### Strengths

- easy to explain through user scenarios
- handles cold-start and weak-signal cases clearly
- practical for app behavior and UX

### Weaknesses

- rules are manually designed
- threshold choices may still feel heuristic
- may oversimplify nuanced user cases

### Best use case

- when the app experience matters
- when the team wants a user-aware hybrid story

### Fit for GMN

Very high. The project already contains fallback logic, so this is a natural extension.

## 4. Adaptive or Confidence-Based Hybrid

### How it works

The system changes the blend weights per user or per prediction case based on confidence signals such as:

- user interaction count
- recommendation coverage
- model score strength
- agreement between content and collaborative signals

Example:

- few ratings -> content-heavy
- many ratings -> collaborative-heavy
- strong agreement -> bonus

### Strengths

- more intelligent than a fixed blend
- aligns better with user-level variation
- stronger design story than simple hard-coded weights

### Weaknesses

- more complex to implement and explain
- confidence definitions must be justified
- validation becomes more important

### Best use case

- when the team wants a more advanced hybrid without moving fully into machine learning-based reranking

### Fit for GMN

Strong. This is likely the best middle ground between simplicity and sophistication.

## 5. Cascade Hybrid

### How it works

One model produces candidate movies first, and another model reranks them afterward.

Example:

- collaborative model generates candidates
- content model reranks for thematic match

or:

- content generates candidates
- collaborative reranks by behavior evidence

### Strengths

- lets each model play a distinct role
- useful for multi-stage recommendation flows
- can improve final ranking quality

### Weaknesses

- more architecture decisions are needed
- harder to validate cleanly
- less transparent than a simple weighted blend

### Best use case

- when the team wants staged recommendation logic rather than one blended score

### Fit for GMN

Moderate. Interesting, but probably more complexity than needed unless the team specifically wants staged routing.

## 6. Learned Hybrid or Meta-Model

### How it works

A supervised model learns how to combine recommendation signals and metadata features.

Possible models:

- logistic regression
- gradient boosting
- learning-to-rank approaches

Possible inputs:

- content score
- collaborative score
- overlap flag
- user activity count
- movie popularity
- genre affinity

### Strengths

- most flexible
- can outperform manual weighting
- strongest advanced extension story

### Weaknesses

- highest complexity
- more difficult to explain
- requires careful training/validation design
- can be too ambitious if time is limited

### Best use case

- when the team wants an advanced final extension or future-work direction

### Fit for GMN

Good as an experimental extension, but probably too complex to replace the main router unless the team fully commits to it.

## User-Scenario View

One useful way to compare strategies is by user type.

### New user

- best choices:
  - fallback
  - content-first
  - rule-based hybrid

### Low-activity user

- best choices:
  - content-heavy hybrid
  - adaptive hybrid

### Active user

- best choices:
  - collaborative-heavy hybrid
  - balanced weighted hybrid
  - adaptive hybrid

### User with no generated recommendation rows

- best choices:
  - fallback
  - switching logic

## Recommended Team Options

### Option A: Keep the current weighted hybrid

Choose this if the team values:

- simplicity
- explainability
- low implementation risk

Best version of this option:

- keep the weighted router
- tune the weights using validation results

### Option B: Upgrade to a rule-based or adaptive hybrid

Choose this if the team values:

- stronger user-level logic
- better handling of cold-start and sparse users
- a more thoughtful app experience

Best version of this option:

- fallback for zero or no-row users
- content-heavy routing for light users
- balanced or collaborative-heavy routing for active users

### Option C: Add a learned hybrid as an experimental extension

Choose this if the team values:

- advanced modeling
- innovation
- extra technical ambition

Best version of this option:

- keep the weighted or adaptive hybrid as the main system
- present the learned model as an extension rather than a replacement

## Final Recommendation

For the GMN project, the strongest practical choices are:

1. `Validation-tuned weighted hybrid`
   Best if the team wants a polished and defendable final system with minimal disruption.

2. `Adaptive or confidence-based hybrid`
   Best if the team wants a more advanced and user-aware hybrid design without moving fully into a learned reranker.

3. `Learned hybrid as future work or experimental add-on`
   Best if the team wants an advanced extension, but not necessarily the main final pipeline.

## Suggested Discussion Questions

- Do we want the final hybrid to stay simple and explainable, or become more adaptive?
- Is the team comfortable defending manually chosen weights, or do we want evidence-based tuning?
- Do we want one global hybrid rule for all users, or different behavior for new, low-activity, and active users?
- Should the learned logistic layer remain a side experiment, or become part of the hybrid strategy story?
- Are we optimizing for presentation clarity, implementation feasibility, or technical ambition?
