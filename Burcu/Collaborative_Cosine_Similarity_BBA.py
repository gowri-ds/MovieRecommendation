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

# Column index -> movieID mapping
index_to_movie_id = {i: mid for i, mid in enumerate(pivot.columns)}

conn.close()

print(ratings_matrix.shape)

# -----------------------------
# Cosine Similarity
# -----------------------------
cos_sim_matrix = cosine_similarity(ratings_matrix, ratings_matrix)

# Remove self-similarity
np.fill_diagonal(cos_sim_matrix, 0)


# create a dataframe with the cosine similarities
df = pd.DataFrame(cos_sim_matrix, columns=range(1, len(ratings_matrix)+1))

# find the index of the most similar user (find maximum value across columns)
most_similar_user_list = df.idxmax(axis=1).tolist()

# -------------------------------------
# Cosine Similarity Recommendation
# (based on the most similar user)
# ------------------------------------

recommended_movies = []

# the loop below will iterate over each user (row in the ratings matrix)
for userid in range(len(ratings_matrix)):  # i = 0..610, customer id = i+1

    # movies the target user actually rated (rating >= 0.5)
    user_A_movies_rated = list(np.where(ratings_matrix[userid] >= 0.5)[0])

    # most similar user row index
    sim_user_row = most_similar_user_list[userid] - 1

    # movies the most similar customer really liked (rating >= 4)
    user_sim_fav_movies = list(np.where(ratings_matrix[sim_user_row] >= 4)[0] + 1)

    # recommend liked-by-similar but not rated by the target user
    recos = list(set(user_sim_fav_movies) - set(user_A_movies_rated))

    # sort for easier readability
    recos.sort()
    recommended_movies.append(recos)

# -----------------------------
# Show Results for One User
# -----------------------------

# Show matched user plus recommended titles
# user_index = 0  # user 1 (index 0)
user_index = 399  # user 400 (index 0)

matched_user = most_similar_user_list[user_index]

print(f"User {user_index + 1} is most similar to User {matched_user}")

# --- Recommended movies (Top 5) ---
recommended_movie_indices = recommended_movies[user_index][:5]

recommended_titles = [
    movie_titles.get(index_to_movie_id[mid], f"Unknown Movie {mid}")
    for mid in recommended_movie_indices
]

print("\nTop 5 Recommended movies (rating >= 4 from similar user):")
for title in recommended_titles:
    print(title)

# --- Common highly rated movies ---
matched_user_index = matched_user - 1  # convert to 0-based index

user_movies = set(np.where(ratings_matrix[user_index] >= 4)[0])
matched_movies = set(np.where(ratings_matrix[matched_user_index] >= 4)[0])

common_movies = list(user_movies & matched_movies)[:5]

print(f"\nCommon highly rated movies between User {user_index + 1} and User {matched_user}:")

if common_movies:
    for idx in common_movies:
        title = movie_titles.get(index_to_movie_id[idx], "Unknown")
        print(title)
else:
    print("No common highly rated movies")
