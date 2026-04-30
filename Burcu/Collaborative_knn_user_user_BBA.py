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
# Normalize Ratings (Mean-Centering)
# -----------------------------
counts = (ratings_matrix != 0).sum(axis=1)

user_means = np.divide(
    ratings_matrix.sum(axis=1),
    counts,
    where=counts != 0,
    out=np.zeros_like(counts, dtype=float)
)

ratings_centered = ratings_matrix - user_means[:, None]

# Keep missing ratings as 0
ratings_centered[ratings_matrix == 0] = 0

# Column index -> movieID mapping
index_to_movie_id = {i: mid for i, mid in enumerate(pivot.columns)}

conn.close()

print("Matrix shape:", ratings_matrix.shape)

# -----------------------------
# Cosine Similarity
# -----------------------------
cos_sim_matrix = cosine_similarity(ratings_centered, ratings_centered)

# Remove self-similarity
np.fill_diagonal(cos_sim_matrix, 0)

# -----------------------------
# Precompute sorted neighbors
# -----------------------------
sorted_neighbors = np.argsort(cos_sim_matrix, axis=1)[:, ::-1]

# -----------------------------
# KNN Recommendation
# -----------------------------
K = 17
recommended_movies = []

for userid, user_ratings in enumerate(ratings_matrix):

    # Movies already rated
    user_A_movies_rated = set(np.where(user_ratings >= 1)[0])

    sim_scores = cos_sim_matrix[userid]

    # Get Top-K users (exclude self safely)
    top_k_users = sorted_neighbors[userid][:K]

    movie_scores = {}

    for neighbor in top_k_users:
        similarity = sim_scores[neighbor]

        # Movies neighbor rated highly
        neighbor_movies = np.where(ratings_matrix[neighbor] >= 4)[0]

        for movie in neighbor_movies:
            if movie not in user_A_movies_rated:
                rating = ratings_matrix[neighbor][movie]

                # weighted score
                movie_scores[movie] = movie_scores.get(movie, 0) + similarity * rating

    # Sort by score
    sorted_movies = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)

    recos = [movie for movie, score in sorted_movies]

    recommended_movies.append(recos)

# -----------------------------
# Show Results for One User
# -----------------------------
user_index = 399  # user 400
#user_index = 299  # user 300

print(f"\nUser {user_index + 1} - Top 5 highly rated movies:")

user_movies = np.where(ratings_matrix[user_index] >= 4)[0][:5]

for movie in user_movies:
    title = movie_titles.get(index_to_movie_id[movie], "Unknown")
    print(f"- {title}")

# -----------------------------
# Top 5 Recommendations with scores
# -----------------------------
sim_scores = cos_sim_matrix[user_index]
top_k_users = sorted_neighbors[user_index][:K]

movie_scores = {}

user_A_movies_rated = set(np.where(ratings_matrix[user_index] >= 0.5)[0])

for neighbor in top_k_users:

    similarity = sim_scores[neighbor]
    neighbor_movies = np.where(ratings_matrix[neighbor] >= 4)[0]

    for movie in neighbor_movies:

        if movie not in user_A_movies_rated:

            rating = ratings_matrix[neighbor][movie]

            movie_scores[movie] = movie_scores.get(movie, 0) + similarity * rating

top_recommendations = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)[:5]

print("\nTop 5 Recommended movies:")

for movie_idx, score in top_recommendations:
    title = movie_titles.get(index_to_movie_id[movie_idx], "Unknown")
    print(f"- {title} (score: {score:.2f})")

# -----------------------------
# Top-5 Similar Users
# -----------------------------
K_display = 5
top_k_users_display = sorted_neighbors[user_index][:K_display]

print(f"\nUser {user_index + 1} Top-{K_display} similar users:")

for u in top_k_users_display:
    print(f"User {int(u)+1} (similarity: {sim_scores[u]:.3f})")

# -----------------------------
# Common Highly Rated Movies
# -----------------------------
user_movies = set(np.where(ratings_matrix[user_index] >= 4)[0])

print(f"\nCommon highly rated movies for User {user_index + 1} with Top-{K_display} similar users:")

for neighbor in top_k_users_display:

    neighbor_movies = set(np.where(ratings_matrix[neighbor] >= 4)[0])

    common_movies = list(user_movies & neighbor_movies)[:5]

    print(f"\nUser {user_index + 1} & User {neighbor + 1}:")

    if common_movies:
        for idx in common_movies:
            title = movie_titles.get(index_to_movie_id[idx], "Unknown")
            print(f"- {title}")
    else:
        print("No common highly rated movies")
