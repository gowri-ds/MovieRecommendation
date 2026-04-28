/* ============================================================
   TF-IDF VS BERT CONTENT SIMILARITY COMPARISON
   ------------------------------------------------------------
   Use these queries after both content similarity pipelines have
   been run:

   - movie_content_similarity_top20
   - movie_content_similarity_bert_top20
   ============================================================ */

/* ------------------------------------------------------------
   0. Helpful comparison indexes
   ------------------------------------------------------------ */

CREATE INDEX IF NOT EXISTS idx_tfidf_base_similar
ON movie_content_similarity_top20(base_movieID, similar_movieID);

CREATE INDEX IF NOT EXISTS idx_bert_base_similar
ON movie_content_similarity_bert_top20(base_movieID, similar_movieID);


/* ------------------------------------------------------------
   1. Total row counts by model
   ------------------------------------------------------------ */

SELECT 'tfidf' AS model_name, COUNT(*) AS row_count
FROM movie_content_similarity_top20
UNION ALL
SELECT 'bert', COUNT(*)
FROM movie_content_similarity_bert_top20;


/* ------------------------------------------------------------
   2. Distinct base movies covered by model
   ------------------------------------------------------------ */

SELECT 'tfidf' AS model_name, COUNT(DISTINCT base_movieID) AS base_movie_count
FROM movie_content_similarity_top20
UNION ALL
SELECT 'bert', COUNT(DISTINCT base_movieID)
FROM movie_content_similarity_bert_top20;


/* ------------------------------------------------------------
   3. TF-IDF sample neighbors for one base movie
   Change base_movieID as needed.
   ------------------------------------------------------------ */

SELECT
    similarity_rank,
    base_movieID,
    similar_movieID,
    similar_title,
    ROUND(similarity_score, 4) AS similarity_score
FROM movie_content_similarity_top20
WHERE base_movieID = 1
ORDER BY similarity_rank;


/* ------------------------------------------------------------
   4. BERT sample neighbors for one base movie
   Change base_movieID as needed.
   ------------------------------------------------------------ */

SELECT
    similarity_rank,
    base_movieID,
    similar_movieID,
    similar_title,
    ROUND(similarity_score, 4) AS similarity_score
FROM movie_content_similarity_bert_top20
WHERE base_movieID = 1
ORDER BY similarity_rank;


/* ------------------------------------------------------------
   5. Average similarity score by model
   ------------------------------------------------------------ */

SELECT
    'tfidf' AS model_name,
    ROUND(AVG(similarity_score), 4) AS avg_similarity_score,
    ROUND(MIN(similarity_score), 4) AS min_similarity_score,
    ROUND(MAX(similarity_score), 4) AS max_similarity_score
FROM movie_content_similarity_top20
UNION ALL
SELECT
    'bert' AS model_name,
    ROUND(AVG(similarity_score), 4) AS avg_similarity_score,
    ROUND(MIN(similarity_score), 4) AS min_similarity_score,
    ROUND(MAX(similarity_score), 4) AS max_similarity_score
FROM movie_content_similarity_bert_top20;


/* ------------------------------------------------------------
   6. Per-movie overlap between TF-IDF and BERT top-20 neighbors
   ------------------------------------------------------------ */

SELECT
    t.base_movieID,
    COUNT(*) AS overlap_count
FROM movie_content_similarity_top20 t
WHERE EXISTS (
    SELECT 1
    FROM movie_content_similarity_bert_top20 b
    WHERE b.base_movieID = t.base_movieID
      AND b.similar_movieID = t.similar_movieID
)
GROUP BY t.base_movieID
ORDER BY overlap_count DESC, t.base_movieID
LIMIT 50;


/* ------------------------------------------------------------
   7. Average overlap across all base movies
   ------------------------------------------------------------ */

WITH overlap AS (
    SELECT
        t.base_movieID,
        COUNT(*) AS overlap_count
    FROM movie_content_similarity_top20 t
    WHERE EXISTS (
        SELECT 1
        FROM movie_content_similarity_bert_top20 b
        WHERE b.base_movieID = t.base_movieID
          AND b.similar_movieID = t.similar_movieID
    )
    GROUP BY t.base_movieID
)
SELECT
    ROUND(AVG(overlap_count), 2) AS avg_overlap_top20
FROM overlap;


/* ------------------------------------------------------------
   8. Movies where TF-IDF and BERT disagree the most
   Lower overlap means larger disagreement.
   ------------------------------------------------------------ */

WITH overlap AS (
    SELECT
        t.base_movieID,
        COUNT(*) AS overlap_count
    FROM movie_content_similarity_top20 t
    WHERE EXISTS (
        SELECT 1
        FROM movie_content_similarity_bert_top20 b
        WHERE b.base_movieID = t.base_movieID
          AND b.similar_movieID = t.similar_movieID
    )
    GROUP BY t.base_movieID
)
SELECT
    m.movieID,
    m.title_clean,
    COALESCE(o.overlap_count, 0) AS overlap_count
FROM movie_content_clean m
LEFT JOIN overlap o
    ON m.movieID = o.base_movieID
ORDER BY overlap_count ASC, m.movieID
LIMIT 50;
