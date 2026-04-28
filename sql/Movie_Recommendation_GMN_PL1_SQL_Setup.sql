/* ======================================================================
   MASTER SQL BUILD SHEET
   PROJECT  : Movie Recommender System
   DATABASE : SQLite

   WHAT THIS SCRIPT DOES
   ----------------------------------------------------------------------
   1) Runs raw-data sanity checks so you can inspect problems early.
   2) Creates a reusable cleaned-tag helper view.
   3) Builds TWO final tables:
        a) movie_content_clean      -> one row per movie
        b) user_movie_interactions  -> one row per user + movie pair
   4) Creates a small set of helper views for content-based recommendation:
        a) vw_movie_genre_split
        b) vw_movie_genre_flags
        c) vw_movie_content_features
   5) Adds indexes so downstream queries stay fast.

   NOTE ABOUT ENRICHMENT
   ----------------------------------------------------------------------
   This script builds the base content layer only.
   TMDB enrichment is handled separately by:
       pipeline/Movie_Recommendation_GMN_PL0_Enrich.py
   That Python step creates:
       - movie_metadata_enriched
       - vw_movie_content_features_enriched
   The downstream content model should prefer the enriched view when it
   exists, but this SQL sheet remains the base setup step.

   DESIGN CHOICES
   ----------------------------------------------------------------------
   - We materialize the two main outputs as TABLES, not views, because they
     will be queried repeatedly during recommendation work.
   - We keep the number of views low.
   - We clean tags once in a helper view and reuse it everywhere.
   - We add timestamp summaries in both Unix and readable datetime format.
   - We include sanity checks at the start and end.

   EXPECTED RAW TABLES
   ----------------------------------------------------------------------
   Movies  (movieID, title, genres)
   Ratings (userID, movieID, rating, timestamp)
   Tags    (userID, movieID, tag, timestamp)
   Links   (movieID, imdbID, tmdbID)
   ====================================================================== */


/* ======================================================================
   SECTION 1: RAW SOURCE SANITY CHECKS
   Why this section exists:
   Before building anything, we want to know whether the raw source tables
   have duplicates, nulls, or structure issues that can create wrong joins.
   These are read-only checks.
   ====================================================================== */

-- List all current tables and views.
SELECT name, type
FROM sqlite_master
WHERE type IN ('table', 'view')
ORDER BY type, name;

-- Raw row counts.
SELECT COUNT(*) AS movies_count  FROM Movies;
SELECT COUNT(*) AS ratings_count FROM Ratings;
SELECT COUNT(*) AS tags_count    FROM Tags;
SELECT COUNT(*) AS links_count   FROM Links;

-- Movies should normally have one row per movieID.
SELECT
    COUNT(*) AS total_movie_rows,
    COUNT(DISTINCT movieID) AS distinct_movie_ids
FROM Movies;

SELECT movieID, COUNT(*) AS duplicate_count
FROM Movies
GROUP BY movieID
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, movieID;

-- Ratings should usually have one row per userID + movieID.
-- If duplicates exist, we will still protect the final interaction table.
SELECT userID, movieID, COUNT(*) AS duplicate_count
FROM Ratings
GROUP BY userID, movieID
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, userID, movieID;

-- Exact duplicate tag rows.
SELECT userID, movieID, tag, timestamp, COUNT(*) AS duplicate_count
FROM Tags
GROUP BY userID, movieID, tag, timestamp
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, userID, movieID;

-- Links should normally have one row per movieID.
SELECT
    COUNT(*) AS total_link_rows,
    COUNT(DISTINCT movieID) AS distinct_link_movie_ids
FROM Links;

SELECT movieID, COUNT(*) AS duplicate_count
FROM Links
GROUP BY movieID
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, movieID;

-- Null / blank checks that often break cleaning logic.
SELECT COUNT(*) AS blank_or_null_title_count
FROM Movies
WHERE title IS NULL OR TRIM(title) = '';

SELECT COUNT(*) AS blank_or_null_genres_count
FROM Movies
WHERE genres IS NULL OR TRIM(genres) = '';

SELECT COUNT(*) AS blank_or_null_tag_count
FROM Tags
WHERE tag IS NULL OR TRIM(tag) = '';

SELECT COUNT(*) AS null_imdbid_count
FROM Links
WHERE imdbID IS NULL;

SELECT COUNT(*) AS null_tmdbid_count
FROM Links
WHERE tmdbID IS NULL;


/* ======================================================================
   SECTION 2: PERFORMANCE INDEXES ON RAW TABLES
   Why this section exists:
   These indexes speed up the table build itself and also help future joins.
   They are safe to keep.
   ====================================================================== */

CREATE INDEX IF NOT EXISTS idx_movies_movieid
    ON Movies(movieID);

CREATE INDEX IF NOT EXISTS idx_ratings_movieid
    ON Ratings(movieID);

CREATE INDEX IF NOT EXISTS idx_ratings_userid_movieid
    ON Ratings(userID, movieID);

CREATE INDEX IF NOT EXISTS idx_tags_movieid
    ON Tags(movieID);

CREATE INDEX IF NOT EXISTS idx_tags_userid_movieid
    ON Tags(userID, movieID);

CREATE INDEX IF NOT EXISTS idx_links_movieid
    ON Links(movieID);


/* ======================================================================
   SECTION 3: DROP OLD OBJECTS
   Why this section exists:
   Re-running the script should fully refresh the cleaned layer.
   We drop views before tables when they depend on the tables.
   ====================================================================== */

DROP VIEW  IF EXISTS vw_movie_content_features;
DROP VIEW  IF EXISTS vw_movie_genre_flags;
DROP VIEW  IF EXISTS vw_movie_genre_split;
DROP VIEW  IF EXISTS vw_tag_rows_clean;

DROP TABLE IF EXISTS user_movie_interactions;
DROP TABLE IF EXISTS movie_content_clean;


/* ======================================================================
   SECTION 4: HELPER VIEW - CLEAN TAG ROWS
   Why this section exists:
   Tags are useful for content recommendation, but raw tags are messy.
   We standardize them once here and reuse this cleaned output in both final
   tables.

   Cleaning rules:
   - remove null / blank tags
   - lowercase all tags
   - trim extra spaces
   - remove repeated words within the same tag row
     Example: 'pixar pixar movie' -> 'pixar movie'
   ====================================================================== */

CREATE VIEW vw_tag_rows_clean AS
WITH RECURSIVE

base_tags AS (
    SELECT
        userID,
        movieID,
        timestamp AS tag_timestamp_unix,
        LOWER(TRIM(tag)) AS raw_tag
    FROM Tags
    WHERE tag IS NOT NULL
      AND TRIM(tag) <> ''
),

split_words AS (
    SELECT
        userID,
        movieID,
        tag_timestamp_unix,
        raw_tag,
        CASE
            WHEN INSTR(raw_tag || ' ', ' ') > 0
                THEN SUBSTR(raw_tag || ' ', 1, INSTR(raw_tag || ' ', ' ') - 1)
            ELSE raw_tag
        END AS word,
        LTRIM(SUBSTR(raw_tag || ' ', INSTR(raw_tag || ' ', ' ') + 1)) AS rest,
        1 AS word_position
    FROM base_tags

    UNION ALL

    SELECT
        userID,
        movieID,
        tag_timestamp_unix,
        raw_tag,
        CASE
            WHEN INSTR(rest, ' ') > 0
                THEN SUBSTR(rest, 1, INSTR(rest, ' ') - 1)
            ELSE rest
        END AS word,
        LTRIM(SUBSTR(rest, INSTR(rest, ' ') + 1)) AS rest,
        word_position + 1 AS word_position
    FROM split_words
    WHERE rest <> ''
),

first_occurrence_per_word AS (
    SELECT
        userID,
        movieID,
        tag_timestamp_unix,
        raw_tag,
        word,
        MIN(word_position) AS first_word_position
    FROM split_words
    WHERE TRIM(word) <> ''
    GROUP BY userID, movieID, tag_timestamp_unix, raw_tag, word
),

rebuilt_tags AS (
    SELECT
        userID,
        movieID,
        tag_timestamp_unix,
        raw_tag,
        GROUP_CONCAT(word, ' ') AS tag_clean
    FROM (
        SELECT
            userID,
            movieID,
            tag_timestamp_unix,
            raw_tag,
            word
        FROM first_occurrence_per_word
        ORDER BY userID, movieID, tag_timestamp_unix, raw_tag, first_word_position
    ) ordered_words
    GROUP BY userID, movieID, tag_timestamp_unix, raw_tag
)

SELECT
    userID,
    movieID,
    tag_timestamp_unix,
    datetime(tag_timestamp_unix, 'unixepoch') AS tag_datetime,
    raw_tag AS original_tag,
    tag_clean
FROM rebuilt_tags;


/* ======================================================================
   SECTION 5: BUILD TABLE 1 - MOVIE CONTENT CLEAN
   Why this section exists:
   This is the main movie-level table for recommendation work.
   It gives you one row per movie with cleaned movie attributes, rating
   summary, cleaned tag summary, and external links.

   IMPORTANT:
   - This table is materialized for speed.
   - This is the table you will mostly use for content-based recommender work.
   ====================================================================== */

CREATE TABLE movie_content_clean AS
WITH

movies_clean AS (
    SELECT
        m.movieID,
        TRIM(m.title) AS title,
        CASE
            WHEN TRIM(m.title) GLOB '*([0-9][0-9][0-9][0-9])'
                THEN TRIM(SUBSTR(TRIM(m.title), 1, LENGTH(TRIM(m.title)) - 6))
            ELSE TRIM(m.title)
        END AS title_clean,
        CASE
            WHEN TRIM(m.title) GLOB '*([0-9][0-9][0-9][0-9])'
                THEN CAST(SUBSTR(TRIM(m.title), LENGTH(TRIM(m.title)) - 4, 4) AS INTEGER)
            ELSE NULL
        END AS release_year,
        CASE
            WHEN m.genres IS NULL OR TRIM(m.genres) = '' THEN '(no genres listed)'
            WHEN LOWER(TRIM(m.genres)) = '(no genres listed)' THEN '(no genres listed)'
            ELSE LOWER(TRIM(m.genres))
        END AS genres_pipe,
        CASE
            WHEN m.genres IS NULL OR TRIM(m.genres) = '' THEN '(no genres listed)'
            WHEN LOWER(TRIM(m.genres)) = '(no genres listed)' THEN '(no genres listed)'
            ELSE REPLACE(LOWER(TRIM(m.genres)), '|', ', ')
        END AS genres_comma
    FROM Movies m
),

ratings_by_movie AS (
    SELECT
        movieID,
        COUNT(*) AS rating_count,
        ROUND(AVG(rating), 3) AS avg_rating,
        MIN(rating) AS min_rating,
        MAX(rating) AS max_rating,
        MIN(timestamp) AS first_rating_timestamp_unix,
        MAX(timestamp) AS last_rating_timestamp_unix
    FROM Ratings
    GROUP BY movieID
),

movie_tags_distinct AS (
    SELECT DISTINCT
        movieID,
        tag_clean
    FROM vw_tag_rows_clean
),

movie_tags_rollup AS (
    SELECT
        d.movieID,
        (
            SELECT GROUP_CONCAT(tag_clean, ' | ')
            FROM (
                SELECT tag_clean
                FROM movie_tags_distinct d2
                WHERE d2.movieID = d.movieID
                ORDER BY tag_clean
            ) ordered_tags
        ) AS all_tags,
        COUNT(*) AS unique_tag_count
    FROM movie_tags_distinct d
    GROUP BY d.movieID
),

movie_tag_time AS (
    SELECT
        movieID,
        MIN(tag_timestamp_unix) AS first_tag_timestamp_unix,
        MAX(tag_timestamp_unix) AS last_tag_timestamp_unix
    FROM vw_tag_rows_clean
    GROUP BY movieID
),

links_one_row AS (
    SELECT
        l.movieID,
        MAX(l.imdbID) AS imdbID,
        MAX(l.tmdbID) AS tmdbID
    FROM Links l
    GROUP BY l.movieID
)

SELECT
    m.movieID,
    m.title,
    m.title_clean,
    m.release_year,
    m.genres_pipe,
    m.genres_comma,

    r.rating_count,
    r.avg_rating,
    r.min_rating,
    r.max_rating,
    r.first_rating_timestamp_unix,
    datetime(r.first_rating_timestamp_unix, 'unixepoch') AS first_rating_datetime,
    r.last_rating_timestamp_unix,
    datetime(r.last_rating_timestamp_unix, 'unixepoch') AS last_rating_datetime,

    tr.all_tags,
    tr.unique_tag_count,
    tt.first_tag_timestamp_unix,
    datetime(tt.first_tag_timestamp_unix, 'unixepoch') AS first_tag_datetime,
    tt.last_tag_timestamp_unix,
    datetime(tt.last_tag_timestamp_unix, 'unixepoch') AS last_tag_datetime,

    lk.imdbID,
    lk.tmdbID,
    'https://movielens.org/movies/' || m.movieID AS movielens_url,
    CASE
        WHEN lk.imdbID IS NOT NULL THEN 'https://www.imdb.com/title/tt' || printf('%07d', CAST(lk.imdbID AS INTEGER))
        ELSE NULL
    END AS imdb_url,
    CASE
        WHEN lk.tmdbID IS NOT NULL THEN 'https://www.themoviedb.org/movie/' || lk.tmdbID
        ELSE NULL
    END AS tmdb_url
FROM movies_clean m
LEFT JOIN ratings_by_movie r
    ON m.movieID = r.movieID
LEFT JOIN movie_tags_rollup tr
    ON m.movieID = tr.movieID
LEFT JOIN movie_tag_time tt
    ON m.movieID = tt.movieID
LEFT JOIN links_one_row lk
    ON m.movieID = lk.movieID;


/* ======================================================================
   SECTION 6: INDEXES ON MOVIE CONTENT CLEAN
   Why this section exists:
   These indexes make movie lookups, title lookups, and movie joins fast.
   ====================================================================== */

CREATE UNIQUE INDEX IF NOT EXISTS idx_movie_content_clean_movieid
    ON movie_content_clean(movieID);

CREATE INDEX IF NOT EXISTS idx_movie_content_clean_title_clean
    ON movie_content_clean(title_clean);

CREATE INDEX IF NOT EXISTS idx_movie_content_clean_release_year
    ON movie_content_clean(release_year);

CREATE INDEX IF NOT EXISTS idx_movie_content_clean_avg_rating
    ON movie_content_clean(avg_rating);


/* ======================================================================
   SECTION 7: BUILD TABLE 2 - USER MOVIE INTERACTIONS
   Why this section exists:
   This table gives one row per userID + movieID pair and keeps the user side
   of the data separate from the movie side.

   What is included:
   - aggregated rating information per user + movie
   - cleaned user tags per user + movie
   - timestamp summaries
   - flags showing whether rating and/or tag data exists

   Why we aggregate here:
   Even though MovieLens typically has one rating per user + movie, this makes
   the table resilient if duplicates exist in the raw data.
   ====================================================================== */

CREATE TABLE user_movie_interactions AS
WITH

rating_events AS (
    SELECT
        userID,
        movieID,
        COUNT(*) AS rating_event_count,
        ROUND(AVG(rating), 3) AS rating_value,
        MIN(timestamp) AS first_rating_timestamp_unix,
        MAX(timestamp) AS last_rating_timestamp_unix
    FROM Ratings
    GROUP BY userID, movieID
),

user_tags_distinct AS (
    SELECT DISTINCT
        userID,
        movieID,
        tag_clean
    FROM vw_tag_rows_clean
),

user_tag_rollup AS (
    SELECT
        d.userID,
        d.movieID,
        (
            SELECT GROUP_CONCAT(tag_clean, ' | ')
            FROM (
                SELECT tag_clean
                FROM user_tags_distinct d2
                WHERE d2.userID = d.userID
                  AND d2.movieID = d.movieID
                ORDER BY tag_clean
            ) ordered_tags
        ) AS user_tags,
        COUNT(*) AS user_unique_tag_count
    FROM user_tags_distinct d
    GROUP BY d.userID, d.movieID
),

user_tag_time AS (
    SELECT
        userID,
        movieID,
        MIN(tag_timestamp_unix) AS first_tag_timestamp_unix,
        MAX(tag_timestamp_unix) AS last_tag_timestamp_unix
    FROM vw_tag_rows_clean
    GROUP BY userID, movieID
),

interaction_keys AS (
    SELECT DISTINCT userID, movieID FROM Ratings
    UNION
    SELECT DISTINCT userID, movieID FROM Tags
)

SELECT
    k.userID,
    k.movieID,

    r.rating_event_count,
    r.rating_value,
    r.first_rating_timestamp_unix,
    datetime(r.first_rating_timestamp_unix, 'unixepoch') AS first_rating_datetime,
    r.last_rating_timestamp_unix,
    datetime(r.last_rating_timestamp_unix, 'unixepoch') AS last_rating_datetime,

    t.user_tags,
    t.user_unique_tag_count,
    tt.first_tag_timestamp_unix,
    datetime(tt.first_tag_timestamp_unix, 'unixepoch') AS first_tag_datetime,
    tt.last_tag_timestamp_unix,
    datetime(tt.last_tag_timestamp_unix, 'unixepoch') AS last_tag_datetime,

    CASE WHEN r.userID IS NOT NULL THEN 1 ELSE 0 END AS has_rating,
    CASE WHEN t.userID IS NOT NULL THEN 1 ELSE 0 END AS has_tag
FROM interaction_keys k
LEFT JOIN rating_events r
    ON k.userID = r.userID
   AND k.movieID = r.movieID
LEFT JOIN user_tag_rollup t
    ON k.userID = t.userID
   AND k.movieID = t.movieID
LEFT JOIN user_tag_time tt
    ON k.userID = tt.userID
   AND k.movieID = tt.movieID;


/* ======================================================================
   SECTION 8: INDEXES ON USER MOVIE INTERACTIONS
   Why this section exists:
   These indexes keep user-level filtering and movie joins fast.
   ====================================================================== */

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_movie_interactions_user_movie
    ON user_movie_interactions(userID, movieID);

CREATE INDEX IF NOT EXISTS idx_user_movie_interactions_movieid
    ON user_movie_interactions(movieID);

CREATE INDEX IF NOT EXISTS idx_user_movie_interactions_userid
    ON user_movie_interactions(userID);

CREATE INDEX IF NOT EXISTS idx_user_movie_interactions_rating_value
    ON user_movie_interactions(rating_value);


/* ======================================================================
   SECTION 9: VIEW - GENRE SPLIT
   Why this section exists:
   Content recommenders often need one row per movie + genre for analysis,
   validation, and later feature engineering.
   ====================================================================== */

CREATE VIEW vw_movie_genre_split AS
WITH RECURSIVE genre_split AS (
    SELECT
        movieID,
        title,
        title_clean,
        release_year,
        genres_pipe,
        CASE
            WHEN genres_pipe = '(no genres listed)' THEN '(no genres listed)'
            WHEN INSTR(genres_pipe, '|') > 0 THEN TRIM(SUBSTR(genres_pipe, 1, INSTR(genres_pipe, '|') - 1))
            ELSE TRIM(genres_pipe)
        END AS genre,
        CASE
            WHEN genres_pipe = '(no genres listed)' THEN ''
            WHEN INSTR(genres_pipe, '|') > 0 THEN SUBSTR(genres_pipe, INSTR(genres_pipe, '|') + 1)
            ELSE ''
        END AS rest
    FROM movie_content_clean

    UNION ALL

    SELECT
        movieID,
        title,
        title_clean,
        release_year,
        genres_pipe,
        CASE
            WHEN INSTR(rest, '|') > 0 THEN TRIM(SUBSTR(rest, 1, INSTR(rest, '|') - 1))
            ELSE TRIM(rest)
        END AS genre,
        CASE
            WHEN INSTR(rest, '|') > 0 THEN SUBSTR(rest, INSTR(rest, '|') + 1)
            ELSE ''
        END AS rest
    FROM genre_split
    WHERE rest <> ''
)
SELECT
    movieID,
    title,
    title_clean,
    release_year,
    genres_pipe,
    genre
FROM genre_split;


/* ======================================================================
   SECTION 10: VIEW - GENRE FLAGS
   Why this section exists:
   This gives one-hot genre columns that are directly useful for a content-
   based recommender, cosine similarity, or feature export to Python/Tableau.
   ====================================================================== */

CREATE VIEW vw_movie_genre_flags AS
SELECT
    movieID,
    MAX(CASE WHEN genre = 'action' THEN 1 ELSE 0 END) AS genre_action,
    MAX(CASE WHEN genre = 'adventure' THEN 1 ELSE 0 END) AS genre_adventure,
    MAX(CASE WHEN genre = 'animation' THEN 1 ELSE 0 END) AS genre_animation,
    MAX(CASE WHEN genre = 'children' THEN 1 ELSE 0 END) AS genre_children,
    MAX(CASE WHEN genre = 'comedy' THEN 1 ELSE 0 END) AS genre_comedy,
    MAX(CASE WHEN genre = 'crime' THEN 1 ELSE 0 END) AS genre_crime,
    MAX(CASE WHEN genre = 'documentary' THEN 1 ELSE 0 END) AS genre_documentary,
    MAX(CASE WHEN genre = 'drama' THEN 1 ELSE 0 END) AS genre_drama,
    MAX(CASE WHEN genre = 'fantasy' THEN 1 ELSE 0 END) AS genre_fantasy,
    MAX(CASE WHEN genre = 'film-noir' THEN 1 ELSE 0 END) AS genre_film_noir,
    MAX(CASE WHEN genre = 'horror' THEN 1 ELSE 0 END) AS genre_horror,
    MAX(CASE WHEN genre = 'imax' THEN 1 ELSE 0 END) AS genre_imax,
    MAX(CASE WHEN genre = 'musical' THEN 1 ELSE 0 END) AS genre_musical,
    MAX(CASE WHEN genre = 'mystery' THEN 1 ELSE 0 END) AS genre_mystery,
    MAX(CASE WHEN genre = 'romance' THEN 1 ELSE 0 END) AS genre_romance,
    MAX(CASE WHEN genre = 'sci-fi' THEN 1 ELSE 0 END) AS genre_sci_fi,
    MAX(CASE WHEN genre = 'thriller' THEN 1 ELSE 0 END) AS genre_thriller,
    MAX(CASE WHEN genre = 'war' THEN 1 ELSE 0 END) AS genre_war,
    MAX(CASE WHEN genre = 'western' THEN 1 ELSE 0 END) AS genre_western,
    MAX(CASE WHEN genre = '(no genres listed)' THEN 1 ELSE 0 END) AS genre_no_genres_listed
FROM vw_movie_genre_split
GROUP BY movieID;


/* ======================================================================
   SECTION 11: VIEW - CONTENT FEATURES
   Why this section exists:
   This is the practical movie feature view for the content recommender.
   It combines the cleaned movie table with one-hot genre flags and adds a
   single combined_text field that is convenient for TF-IDF or keyword-based
   experiments later.
   ====================================================================== */

CREATE VIEW vw_movie_content_features AS
SELECT
    m.movieID,
    m.title,
    m.title_clean,
    m.release_year,
    m.genres_pipe,
    m.genres_comma,
    m.rating_count,
    m.avg_rating,
    m.min_rating,
    m.max_rating,
    m.all_tags,
    m.unique_tag_count,
    m.imdbID,
    m.tmdbID,
    m.movielens_url,
    m.imdb_url,
    m.tmdb_url,

    TRIM(
        COALESCE(m.title_clean, '') || ' ' ||
        COALESCE(REPLACE(m.genres_comma, ',', ' '), '') || ' ' ||
        COALESCE(REPLACE(m.all_tags, '|', ' '), '')
    ) AS combined_text,

    g.genre_action,
    g.genre_adventure,
    g.genre_animation,
    g.genre_children,
    g.genre_comedy,
    g.genre_crime,
    g.genre_documentary,
    g.genre_drama,
    g.genre_fantasy,
    g.genre_film_noir,
    g.genre_horror,
    g.genre_imax,
    g.genre_musical,
    g.genre_mystery,
    g.genre_romance,
    g.genre_sci_fi,
    g.genre_thriller,
    g.genre_war,
    g.genre_western,
    g.genre_no_genres_listed
FROM movie_content_clean m
LEFT JOIN vw_movie_genre_flags g
    ON m.movieID = g.movieID;


/* ======================================================================
   SECTION 12: POST-BUILD VALIDATION CHECKS
   Why this section exists:
   These checks confirm that the final objects match the expected grain.
   Run them after the build completes.
   ====================================================================== */

-- movie_content_clean should have one row per movie.
SELECT
    COUNT(*) AS movie_content_rows,
    COUNT(DISTINCT movieID) AS distinct_movie_ids
FROM movie_content_clean;

-- user_movie_interactions should have one row per userID + movieID pair.
SELECT
    COUNT(*) AS interaction_rows,
    COUNT(DISTINCT userID || '-' || movieID) AS distinct_user_movie_pairs
FROM user_movie_interactions;

-- Sanity check movies with no genres after cleaning.
SELECT COUNT(*) AS no_genre_rows_after_cleaning
FROM movie_content_clean
WHERE genres_pipe IS NULL OR TRIM(genres_pipe) = '';

-- Sanity check how many movies have no ratings.
SELECT COUNT(*) AS movies_without_ratings
FROM movie_content_clean
WHERE rating_count IS NULL;

-- Sanity check how many movies have no tags.
SELECT COUNT(*) AS movies_without_tags
FROM movie_content_clean
WHERE unique_tag_count IS NULL;

-- Sanity check for duplicate rows in the final user table.
SELECT userID, movieID, COUNT(*) AS duplicate_count
FROM user_movie_interactions
GROUP BY userID, movieID
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, userID, movieID;

-- Quick sample of the movie table.
SELECT *
FROM movie_content_clean
LIMIT 10;

-- Quick sample of the user interaction table.
SELECT *
FROM user_movie_interactions
LIMIT 10;

-- Quick sample of the content feature view.
SELECT *
FROM vw_movie_content_features
LIMIT 10;



/* ======================================================================
   SECTION 13: USEFUL STARTER QUERIES
   Why this section exists:
   These are ready-to-use checks for your next step in the recommender work.
   ====================================================================== */

-- 1) Find movies whose title contains 'toy'.
SELECT movieID, title, title_clean, genres_comma, avg_rating
FROM movie_content_clean
WHERE LOWER(title) LIKE '%toy%'
ORDER BY title;

-- 2) Check whether a specific movie exists.
SELECT movieID, title, title_clean, genres_comma, imdb_url, tmdb_url
FROM movie_content_clean
WHERE LOWER(title) LIKE '%inception%';

-- 3) Get all distinct genres and movie counts.
SELECT genre, COUNT(*) AS movie_count
FROM vw_movie_genre_split
GROUP BY genre
ORDER BY genre;

-- 4) Count how many movies contain the genre 'war'.
SELECT COUNT(DISTINCT movieID) AS war_movie_count
FROM vw_movie_genre_split
WHERE LOWER(genre) = 'war';

-- 5) Start point for content recommendation feature extraction.
SELECT *
FROM vw_movie_content_features
WHERE movieID = 1;
