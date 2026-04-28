/*
========================================================================
COLLABORATIVE KNN LEAVE-ONE-OUT SQL TESTING QUERIES
========================================================================
Purpose:
    Validate and inspect the output of the collaborative KNN tuning step.

Source tables:
    collaborative_knn_leave_one_out_user_results
    collaborative_knn_leave_one_out_summary
========================================================================
*/

/*
Query 1: Confirm the output tables exist
*/
SELECT name
FROM sqlite_master
WHERE type = 'table'
  AND name IN (
      'collaborative_knn_leave_one_out_user_results',
      'collaborative_knn_leave_one_out_summary'
  )
ORDER BY name;


/*
Query 2: Summary by K value
*/
SELECT
    k_neighbors,
    evaluation_top_n,
    eligible_users,
    hits,
    ROUND(hit_rate_at_n, 4) AS hit_rate_at_n
FROM collaborative_knn_leave_one_out_summary
ORDER BY hit_rate_at_n DESC, k_neighbors;


/*
Query 3: Best K value
*/
SELECT
    k_neighbors,
    evaluation_top_n,
    eligible_users,
    hits,
    ROUND(hit_rate_at_n, 4) AS hit_rate_at_n
FROM collaborative_knn_leave_one_out_summary
ORDER BY hit_rate_at_n DESC, hits DESC, k_neighbors
LIMIT 1;


/*
Query 4: User-level rows for one K value
*/
SELECT
    userID,
    k_neighbors,
    holdout_movieID,
    holdout_title,
    hit,
    hit_rank
FROM collaborative_knn_leave_one_out_user_results
WHERE k_neighbors = 9
ORDER BY userID
LIMIT 25;


/*
Query 5: Hit counts by K value
*/
SELECT
    k_neighbors,
    COUNT(*) AS evaluated_users,
    SUM(hit) AS hits,
    ROUND(AVG(hit), 4) AS hit_rate_at_n
FROM collaborative_knn_leave_one_out_user_results
GROUP BY k_neighbors
ORDER BY hit_rate_at_n DESC, k_neighbors;
