"""
========================================================================
TMDB METADATA ENRICHMENT SCRIPT
========================================================================
Purpose:
    Fetches movie metadata from the TMDB API for each movie that has
    a tmdbID in the Links table. Stores results in a new SQLite table
    movie_metadata_enriched.

What this script creates:
    Table : movie_metadata_enriched
    View  : vw_movie_content_features_enriched

    The enriched view extends combined_text with:
        overview, top keywords, director, top cast

Why this helps:
    The current TF-IDF model uses only title + genres + user tags.
    Tags are sparse — most movies have few or none. Adding TMDB plot
    descriptions and structured keywords gives the model much richer
    text to differentiate movies that share the same genre combination.

Resume-friendly:
    Each movie is skipped if it already has a row in
    movie_metadata_enriched. Re-running the script safely picks up
    where it left off after any interruption.

Quick-test mode:
    Set QUICK_TEST = True to run on the first 100 movies only.
    Use this to validate API access and check enrichment quality
    before committing to the full ~60-minute run.

API rate limits:
    TMDB free tier: ~40 requests/second across 3 calls per movie.
    SLEEP_BETWEEN_MOVIES = 0.25 seconds is safe and keeps the full
    run under 60 minutes.

Before running:
    1. Get a free TMDB API key at https://www.themoviedb.org/settings/api
    2. Add it to config.py as TMDB_API_KEY
    3. Run PL1 SQL setup first (movie_content_clean must exist)
    4. Run this script (PL0) before re-running PL2
========================================================================
"""

import sqlite3
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------
# USER SETTINGS  — update these before running
# ---------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import DB_PATH, TMDB_API_KEY

QUICK_TEST           = False   # set False to run all 9,742 movies
QUICK_TEST_LIMIT     = 100     # number of movies to test with
SLEEP_BETWEEN_MOVIES = 0.25    # seconds between movies (3 API calls each)

TOP_CAST_COUNT    = 5          # how many cast members to store
TOP_KEYWORD_COUNT = 10         # how many keywords to store

TMDB_BASE = "https://api.themoviedb.org/3/movie"
TIMEOUT   = 10                 # seconds per API request

# Keywords to exclude (format/technical tags, not content)
EXCLUDED_KEYWORDS = {"imax", "3d", "based on novel", "based on book"}


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def print_divider(char="=", width=72):
    print(char * width)


def table_exists(conn, name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name = ?",
        (name,)
    ).fetchone()
    return row is not None


def already_enriched(conn, movie_id):
    row = conn.execute(
        "SELECT 1 FROM movie_metadata_enriched WHERE movieID = ?",
        (int(movie_id),)
    ).fetchone()
    return row is not None


def clean_text(text):
    """Remove newlines, tabs, extra spaces, and problematic quotes."""
    if not text:
        return ""
    text = str(text)
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = text.replace('"', "").replace("'", "")
    # Collapse multiple spaces
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()


# ---------------------------------------------------------------------
# TMDB API CALLS
# ---------------------------------------------------------------------

def fetch_tmdb(url, params, retries=3):
    """
    Fetch a TMDB endpoint with retry on timeout and 429 rate-limit.
    Returns parsed JSON dict or None on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 404:
                return None  # movie not in TMDB — not an error worth retrying

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                print(f"    Rate limited. Waiting {retry_after}s ...")
                time.sleep(retry_after)
                continue

            # Any other HTTP error
            print(f"    HTTP {resp.status_code} on attempt {attempt}: {url}")

        except requests.Timeout:
            print(f"    Timeout on attempt {attempt}: {url}")
        except requests.RequestException as e:
            print(f"    Request error on attempt {attempt}: {e}")

        if attempt < retries:
            time.sleep(2)

    return None


def fetch_movie_metadata(tmdb_id, api_key):
    """
    Calls three TMDB endpoints for one movie:
        /movie/{id}           -> overview
        /movie/{id}/keywords  -> keywords list
        /movie/{id}/credits   -> cast and director

    Returns a dict of parsed fields, or None if the main call fails.
    """
    params = {"api_key": api_key, "language": "en-US"}
    base   = f"{TMDB_BASE}/{int(tmdb_id)}"

    # Main details
    details = fetch_tmdb(base, params)
    if details is None:
        return None

    overview = clean_text(details.get("overview", ""))

    # Keywords
    kw_data  = fetch_tmdb(f"{base}/keywords", params) or {}
    raw_kws  = [k["name"].lower() for k in kw_data.get("keywords", [])]
    keywords = [k for k in raw_kws if k not in EXCLUDED_KEYWORDS][:TOP_KEYWORD_COUNT]

    # Credits
    cr_data   = fetch_tmdb(f"{base}/credits", params) or {}
    cast_list = [
        clean_text(c["name"])
        for c in sorted(cr_data.get("cast", []), key=lambda x: x.get("order", 999))
        if c.get("name")
    ][:TOP_CAST_COUNT]

    directors = [
        clean_text(c["name"])
        for c in cr_data.get("crew", [])
        if c.get("job") == "Director" and c.get("name")
    ]

    return {
        "overview"      : overview,
        "keywords"      : " ".join(keywords),
        "cast"          : " ".join(cast_list),
        "director"      : directors[0] if directors else "Unknown",
        "keyword_count" : len(keywords),
        "cast_count"    : len(cast_list),
    }


# ---------------------------------------------------------------------
# DATABASE SETUP
# ---------------------------------------------------------------------

def create_enrichment_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS movie_metadata_enriched (
            movieID       INTEGER PRIMARY KEY,
            tmdbID        INTEGER,
            overview      TEXT,
            keywords      TEXT,
            cast          TEXT,
            director      TEXT,
            keyword_count INTEGER,
            cast_count    INTEGER,
            fetch_status  TEXT NOT NULL,
            fetched_at    TEXT NOT NULL
        );
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_enriched_tmdbid
            ON movie_metadata_enriched(tmdbID);
    """)
    conn.commit()


def create_enriched_view(conn):
    """
    Creates vw_movie_content_features_enriched.
    Extends the existing content feature view by appending TMDB fields
    to combined_text.
    """
    conn.execute("DROP VIEW IF EXISTS vw_movie_content_features_enriched;")
    conn.execute("""
        CREATE VIEW vw_movie_content_features_enriched AS
        SELECT
            f.movieID,
            f.title,
            f.title_clean,
            f.release_year,
            f.genres_pipe,
            f.genres_comma,
            f.rating_count,
            f.avg_rating,
            f.all_tags,
            f.imdbID,
            f.tmdbID,
            f.movielens_url,
            f.imdb_url,
            f.tmdb_url,

            e.overview,
            e.keywords      AS tmdb_keywords,
            e.cast          AS tmdb_cast,
            e.director      AS tmdb_director,
            e.fetch_status,

            -- Genre OHE columns pass through unchanged
            f.genre_action,
            f.genre_adventure,
            f.genre_animation,
            f.genre_children,
            f.genre_comedy,
            f.genre_crime,
            f.genre_documentary,
            f.genre_drama,
            f.genre_fantasy,
            f.genre_film_noir,
            f.genre_horror,
            f.genre_imax,
            f.genre_musical,
            f.genre_mystery,
            f.genre_romance,
            f.genre_sci_fi,
            f.genre_thriller,
            f.genre_war,
            f.genre_western,
            f.genre_no_genres_listed,

            -- Enriched combined_text for TF-IDF
            TRIM(
                COALESCE(f.title_clean,   '') || ' ' ||
                COALESCE(REPLACE(f.genres_comma, ',', ' '), '') || ' ' ||
                COALESCE(REPLACE(f.all_tags, '|', ' '), '') || ' ' ||
                COALESCE(e.overview,  '') || ' ' ||
                COALESCE(e.keywords,  '') || ' ' ||
                COALESCE(e.director,  '') || ' ' ||
                COALESCE(e.cast,      '')
            ) AS combined_text

        FROM vw_movie_content_features f
        LEFT JOIN movie_metadata_enriched e
            ON f.movieID = e.movieID
           AND e.fetch_status = 'ok';
    """)
    conn.commit()


# ---------------------------------------------------------------------
# MAIN ENRICHMENT LOOP
# ---------------------------------------------------------------------

def load_movies_to_enrich(conn):
    """
    Returns movies that have a tmdbID but are not yet in the enrichment
    table. Uses the Links table as the source of tmdbID values.
    """
    id_col = "movieID" if any(
        r[1] == "movieID" for r in conn.execute("PRAGMA table_info(Links)").fetchall()
    ) else "movieId"

    query = f"""
        SELECT
            l.{id_col} AS movieID,
            l.tmdbID
        FROM Links l
        WHERE l.tmdbID IS NOT NULL
          AND TRIM(CAST(l.tmdbID AS TEXT)) <> ''
        ORDER BY l.{id_col}
    """
    return pd.read_sql_query(query, conn)


def run_enrichment(conn, movies_df, api_key):
    total      = len(movies_df)
    skipped    = 0
    successful = 0
    failed     = 0
    ts         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx, row in enumerate(movies_df.itertuples(), start=1):
        movie_id = int(row.movieID)
        tmdb_id  = row.tmdbID

        prefix = f"[{idx:>5}/{total}] movieID={movie_id} tmdbID={tmdb_id}"

        # Skip if already done
        if already_enriched(conn, movie_id):
            skipped += 1
            if idx % 500 == 0:
                print(f"{prefix}  SKIP (already enriched)")
            continue

        # Fetch from TMDB
        meta = fetch_movie_metadata(tmdb_id, api_key)

        if meta is not None:
            conn.execute("""
                INSERT OR REPLACE INTO movie_metadata_enriched
                    (movieID, tmdbID, overview, keywords, cast, director,
                     keyword_count, cast_count, fetch_status, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?)
            """, (
                movie_id, int(tmdb_id),
                meta["overview"], meta["keywords"],
                meta["cast"],     meta["director"],
                meta["keyword_count"], meta["cast_count"],
                ts,
            ))
            successful += 1

            # Progress every 100 movies
            if idx % 100 == 0 or idx == total:
                print(f"{prefix}  ok  | success={successful} failed={failed} skipped={skipped}")

        else:
            conn.execute("""
                INSERT OR REPLACE INTO movie_metadata_enriched
                    (movieID, tmdbID, overview, keywords, cast, director,
                     keyword_count, cast_count, fetch_status, fetched_at)
                VALUES (?, ?, '', '', '', 'Unknown', 0, 0, 'failed', ?)
            """, (movie_id, int(tmdb_id), ts))
            failed += 1

            if idx % 100 == 0 or idx == total:
                print(f"{prefix}  FAIL | success={successful} failed={failed} skipped={skipped}")

        conn.commit()
        time.sleep(SLEEP_BETWEEN_MOVIES)

    return successful, failed, skipped


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():
    start_time = datetime.now()

    print_divider()
    print("STARTING TMDB METADATA ENRICHMENT")
    print_divider()
    print(f"Database : {DB_PATH}")
    print(f"Mode     : {'QUICK TEST (first ' + str(QUICK_TEST_LIMIT) + ' movies)' if QUICK_TEST else 'FULL RUN (all movies)'}")
    print(f"Started  : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not TMDB_API_KEY or TMDB_API_KEY == "YOUR_TMDB_API_KEY_HERE":
        print("ERROR: TMDB_API_KEY is not set.")
        print("Get a free key at https://www.themoviedb.org/settings/api")
        print("Then add it to TMDB_API_KEY in config.py.")
        return

    conn = None

    try:
        print("[STEP 1/5] Connecting to database...")
        conn = sqlite3.connect(DB_PATH)
        print("Success.\n")

        print("[STEP 2/5] Creating enrichment table (if not exists)...")
        create_enrichment_table(conn)
        already_done = conn.execute(
            "SELECT COUNT(*) FROM movie_metadata_enriched"
        ).fetchone()[0]
        print(f"Success. {already_done:,} movies already enriched.\n")

        print("[STEP 3/5] Loading movies to enrich...")
        movies_df = load_movies_to_enrich(conn)

        if QUICK_TEST:
            movies_df = movies_df.head(QUICK_TEST_LIMIT)

        print(f"Movies queued: {len(movies_df):,}\n")

        print("[STEP 4/5] Fetching from TMDB API...")
        successful, failed, skipped = run_enrichment(conn, movies_df, TMDB_API_KEY)
        print()

        print("[STEP 5/5] Creating enriched content view...")
        if table_exists(conn, "vw_movie_content_features"):
            create_enriched_view(conn)
            print("Success: vw_movie_content_features_enriched created.\n")
        else:
            print("Skipped: vw_movie_content_features not found.")
            print("Run PL1 SQL setup first, then re-run PL0 to create the view.\n")

        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        total    = successful + failed + skipped

        print_divider()
        print("ENRICHMENT COMPLETED")
        print_divider()
        print(f"  Total movies processed : {total:,}")
        print(f"  Successful             : {successful:,}")
        print(f"  Failed (404/timeout)   : {failed:,}")
        print(f"  Skipped (already done) : {skipped:,}")
        print()

        if QUICK_TEST:
            print("QUICK TEST MODE — next steps:")
            print("  1. Check the sample output below")
            print("  2. If enrichment looks good, set QUICK_TEST = False and re-run")
            print("  3. Then re-run PL2 (TF-IDF) using vw_movie_content_features_enriched")
            print("  4. Re-run PL7 evaluation and compare hit_rate@10 vs 0.0265 (OHE baseline)")
        else:
            print("FULL RUN complete — next steps:")
            print("  1. Update PL2 DB source to vw_movie_content_features_enriched")
            print("  2. Re-run: python run_pipeline.py")
            print("  3. Check evaluation comparison printed by PL7")

        print()

        # Sample output
        sample = pd.read_sql_query("""
            SELECT movieID, director, keyword_count, cast_count,
                   SUBSTR(overview, 1, 80) AS overview_preview,
                   keywords
            FROM movie_metadata_enriched
            WHERE fetch_status = 'ok'
            LIMIT 5
        """, conn)
        print("Sample enriched rows:")
        print(sample.to_string(index=False))

        print()
        print(f"  Finished : {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Runtime  : {duration}")
        print_divider()

    except Exception as e:
        print_divider("!")
        print("ENRICHMENT FAILED")
        print_divider("!")
        print(str(e))
        print(traceback.format_exc())
        print_divider("!")

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
