// Fruit Recommendation
// Parameters: $name, $limit
// Fruits liked by similar users that the user does not like yet.
// SIMILAR_TO is matched without direction, so similarity is symmetric.
MATCH (me:User {name:$name})
      -[:SIMILAR_TO]-(similar:User)
      -[:LIKES]->(fruit:Fruit)
WHERE NOT EXISTS { MATCH (me)-[:LIKES]->(fruit) }
WITH DISTINCT fruit, similar
ORDER BY toLower(similar.name)

// score = number of similar users who like the fruit
RETURN fruit.name AS fruit,
       count(similar) AS score,
       collect(similar.name) AS similar_names
ORDER BY score DESC, fruit
LIMIT $limit;

// Rebuild SIMILAR_TO from shared LIKES (same rule as the homework notebook):
// MATCH (:User)-[r:SIMILAR_TO]-(:User) DELETE r;
// MATCH (u1:User)-[:LIKES]->(:Fruit)<-[:LIKES]-(u2:User)
// WHERE u1.name < u2.name
// MERGE (u1)-[:SIMILAR_TO]->(u2);
