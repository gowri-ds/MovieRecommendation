import numpy as np
import pandas as pd
import sqlite3
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt

np.random.seed(123) # Set a random seed
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

movie_titles = dict(zip(df_data["movieID"], df_data["title"]))

pivot = df_data.pivot(index="userID", columns="movieID", values="rating").fillna(0)

ratings_matrix = pivot.values

# -----------------------------
# Normalize Ratings (Mean-Centering)
# -----------------------------
user_means = np.true_divide(
    ratings_matrix.sum(axis=1),
    (ratings_matrix != 0).sum(axis=1)
)

# Handle users with no ratings (avoid division by zero)
user_means = np.nan_to_num(user_means)

ratings_centered = ratings_matrix - user_means[:, None]

# Keep missing ratings as 0
ratings_centered[ratings_matrix == 0] = 0

index_to_movie_id = {i: mid for i, mid in enumerate(pivot.columns)}

conn.close()

print("Matrix shape:", ratings_matrix.shape)

# -----------------------------
# Cosine Similarity
# -----------------------------
cos_sim_matrix = cosine_similarity(ratings_centered.T, ratings_centered.T)
np.fill_diagonal(cos_sim_matrix, 0)

# -----------------------------
# Precompute sorted neighbors
# -----------------------------
sorted_neighbors = np.argsort(cos_sim_matrix, axis=1)[:, ::-1]

# -----------------------------
# Leave-One-Out Evaluation
# -----------------------------
K_values = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
N=5
hit_rates = {}

for K in K_values:

    hits = 0
    total = 0

    for userid, user_ratings in enumerate(ratings_matrix):

        fav_movies = np.where(user_ratings >= 4)[0]

        if len(fav_movies) < 2:
            continue

        # Random leave-one-out
        test_movie = np.random.choice(fav_movies)

        # Copy ONLY this user's ratings
        temp_user = user_ratings.copy()
        temp_user[test_movie] = 0

        visible_movies = np.where(temp_user >= 4)[0]
        rated_movies = set(np.where(temp_user >= 0.5)[0])

        movie_scores = {}

        for movie in visible_movies:

            sim_scores = cos_sim_matrix[movie]

            # Use precomputed neighbors
            top_k_movies = sorted_neighbors[movie][:K]

            for neighbor_movie in top_k_movies:

                if neighbor_movie not in rated_movies:

                    similarity = sim_scores[neighbor_movie]
                    rating = temp_user[movie]

                    movie_scores[neighbor_movie] = movie_scores.get(neighbor_movie, 0) + similarity * rating

        # Rank recommendations
        if movie_scores:
            ranked_movies = sorted(movie_scores.items(), key=lambda x: x[1], reverse=True)
            top_n = [m for m, _ in ranked_movies[:N]]
        else:
            top_n = []

        # Hit check
        if test_movie in top_n:
            hits += 1

        total += 1

    hit_rate = hits / total if total > 0 else 0
    hit_rates[K] = hit_rate

# -----------------------------
# Print Results
# -----------------------------
print("\nFast Leave-One-Out Hit Rate:")
for k, hr in hit_rates.items():
    print(f"K={k}: Hit Rate = {hr:.4f}")

best_k = max(hit_rates, key=hit_rates.get)
print(f"\nBest K based on Hit Rate: {best_k}")

# -----------------------------
# Plot
# -----------------------------

# Prepare data
K_list = list(hit_rates.keys())
hit_rate_values = list(hit_rates.values())

# Plot
plt.figure(figsize=(8, 5))
plt.plot(K_list, hit_rate_values, marker='o', linewidth=2)
plt.fill_between(K_list, hit_rate_values, alpha=0.1)


# Labels and title
plt.xlabel("K (Neighbors)", fontsize=12)
plt.ylabel("Hit Rate", fontsize=12)
plt.title("Hyperparameter Tuning: K vs Hit Rate", fontsize=14)

# Make it cleaner
plt.xticks(K_list)
plt.grid(alpha=0.3)

# Highlight best K
best_k = max(hit_rates, key=hit_rates.get)
best_hr = hit_rates[best_k]

plt.scatter(best_k, best_hr, color='red', label=f"Best K={best_k}")
plt.legend()

plt.show()



