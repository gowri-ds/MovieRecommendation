import numpy as np
import pandas as pd
import sqlite3
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# Load Data
# -----------------------------
# Connect to the Movies database.

conn = sqlite3.connect(r"/Users/burcu/Documents/MS_BSAN_courses/BSAN780_Spring_2026/Project/Movies.db")
cur = conn.cursor()

cur.execute("SELECT userID, movieID, rating, title FROM User_Movie_Ratings;")

rows = cur.fetchall()

# -----------------------------
# Build DataFrame + Matrix
# -----------------------------

df_data = pd.DataFrame(rows, columns=["userID", "movieID", "rating", "title"])

# MovieID -> Title mapping
movie_titles = dict(zip(df_data["movieID"], df_data["title"]))

# Create user-movie matrix
pivot = df_data.pivot(index="userID", columns="movieID", values="rating").fillna(0)

# Convert to numpy matrix
ratings_matrix = pivot.values

# -----------------------------
# Normalize Ratings
# -----------------------------
counts = (ratings_matrix != 0).sum(axis=1)

user_means = np.divide(
    ratings_matrix.sum(axis=1),
    counts,
    where=counts != 0,
    out = np.zeros_like(counts, dtype=float)
)

ratings_centered = ratings_matrix - user_means[:, None]
ratings_centered[ratings_matrix == 0] = 0

# Column index -> movieID mapping
index_to_movie_id = {i: mid for i, mid in enumerate(pivot.columns)}

conn.close()

print("Matrix shape:", ratings_matrix.shape)

# -----------------------------
# Cosine Similarity
# -----------------------------

# Item-item cosine similarity
cos_sim_matrix = cosine_similarity(ratings_centered.T, ratings_centered.T)

# Remove self-similarity
np.fill_diagonal(cos_sim_matrix, 0)

# -----------------------------
# Precompute sorted neighbors
# -----------------------------
sorted_neighbors = np.argsort(cos_sim_matrix, axis=1)[:, ::-1]

# -----------------------------
# KNN Recommendation
# -----------------------------

K = 9

recommended_movies = []

for userid in range(len(ratings_matrix)):

    # Movies already rated
    user_A_movies_rated = set(np.where(ratings_matrix[userid] >= 0.5)[0])

    # Movies the target user rated highly

    user_A_fav_movies = np.where(ratings_matrix[userid] >= 4)[0]
    movie_scores = {}

    for movie in user_A_fav_movies:
        sim_scores = cos_sim_matrix[movie]

        top_k_movies = sorted_neighbors[movie][:K]

        for neighbor_movie in top_k_movies:
            if neighbor_movie not in user_A_movies_rated:
                similarity = sim_scores[neighbor_movie]

                # rating the target user gave to the source movie
                rating = ratings_matrix[userid][movie]

                # weighted score
                movie_scores[neighbor_movie] = movie_scores.get(neighbor_movie, 0) + similarity * rating

    # Sort by score

    sorted_movies = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)
    recos = [movie for movie, score in sorted_movies]
    recommended_movies.append(recos)

# -----------------------------
# Show Results for One User
# -----------------------------

user_index = 399  # user 400
#user_index = 299  # user 300


# Movies highly rated by the target user (top 5)
user_fav_movies = np.where(ratings_matrix[user_index] >= 4)[0][:5]

print(f"\nUser {user_index + 1} - Top 5 highly rated movies:")

for movie in user_fav_movies:
    title = movie_titles.get(index_to_movie_id[movie], "Unknown")
    print(f"- {title}")

# ----------------------------------
# Compute Top 5 Recommendations with scores
# ----------------------------------
movie_scores = {}

user_A_movies_rated = set(np.where(ratings_matrix[user_index] >= 0.5)[0])

for movie in user_fav_movies:

    sim_scores = cos_sim_matrix[movie]

    top_k_movies = sorted_neighbors[movie][:K]

    for neighbor_movie in top_k_movies:

        if neighbor_movie not in user_A_movies_rated:

            similarity = sim_scores[neighbor_movie]
            rating = ratings_matrix[user_index][movie]

            movie_scores[neighbor_movie] = movie_scores.get(neighbor_movie, 0) + similarity * rating

# -----------------------------
# Top 5 Recommendations
# -----------------------------

top_recommendations = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)[:5]

print("\nTop 5 Recommended Movies:")

for movie_idx, score in top_recommendations:
    title = movie_titles.get(index_to_movie_id[movie_idx], "Unknown")
    print(f"- {title} (score: {score:.2f})")


# -----------------------------
# Top 5 favorites → best match (1-to-1)
# -----------------------------


print(f"\nUser {user_index + 1} - Top 5 highly rated movies and their closest match:\n")

for movie in user_fav_movies:

    sim_scores = cos_sim_matrix[movie]

    # Sort similarities descending
    sorted_indices = np.argsort(sim_scores)[::-1]

    # Find the first valid similar movie (not itself + not already rated)
    best_match = None
    for idx in sorted_indices:
        if idx != movie and ratings_matrix[user_index][idx] < 0.5:
            best_match = idx
            break

    source_title = movie_titles.get(index_to_movie_id[movie], "Unknown")

    if best_match is not None:
        match_title = movie_titles.get(index_to_movie_id[best_match], "Unknown")
        similarity = sim_scores[best_match]

        print(f"{source_title}")
        print(f"  → {match_title} (similarity: {similarity:.3f})\n")
    else:
        print(f"{source_title}")
        print("  → No suitable recommendation found\n")