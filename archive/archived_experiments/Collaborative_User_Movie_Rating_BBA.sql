DROP TABLE IF EXISTS User_Movie_Ratings;
CREATE TABLE IF NOT EXISTS User_Movie_Ratings AS

WITH All_Users AS (
    SELECT DISTINCT userID
    FROM Recommender_Base
),
All_Movies AS (
    SELECT DISTINCT movieID, title, genres
    FROM Recommender_Base
)

SELECT 
    u.userID,
    m.movieID,
	  m.title,
    m.genres,
    CASE 
        WHEN r.rating IS NULL THEN 0
        ELSE r.rating
    END AS rating
FROM All_Users u
CROSS JOIN All_Movies m
LEFT JOIN Recommender_Base r
    ON u.userID = r.userID 
   AND m.movieID = r.movieID
   ORDER BY u.userID, m.movieID;

SELECT * 
FROM User_Movie_Ratings;