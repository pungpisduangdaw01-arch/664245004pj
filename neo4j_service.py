from __future__ import annotations

from typing import Any

import streamlit as st
from neo4j import GraphDatabase, RoutingControl

RELATIONSHIP_TYPES = ["LIKES", "SIMILAR_TO"]

# Sample dataset from homework/03_neo4j/664245004_fruit_2.ipynb
DEMO_USERS = ["Ananda", "Boonchit", "Chutima", "Danai", "boy", "yu", "pond", "pat", "poo", "ya"]
DEMO_FRUITS = ["Mango", "Apple", "Durian", "Banana", "Grape"]
DEMO_LIKES = [
    ["Ananda", "Mango"], ["Ananda", "Apple"],
    ["Boonchit", "Mango"], ["Boonchit", "Apple"], ["Boonchit", "Banana"],
    ["Chutima", "Mango"], ["Chutima", "Durian"],
    ["Danai", "Banana"], ["Danai", "Grape"],
    ["boy", "Durian"], ["boy", "Grape"],
    ["yu", "Mango"], ["yu", "Banana"],
    ["pond", "Apple"], ["pond", "Durian"],
    ["pat", "Grape"], ["pat", "Mango"],
    ["poo", "Banana"], ["poo", "Apple"],
    ["ya", "Durian"], ["ya", "Mango"],
]


def _config() -> tuple[str, str, str, str | None]:
    cfg = st.secrets["neo4j"]
    # No database configured -> None, which makes the driver use the home database.
    return cfg["uri"], cfg["username"], cfg["password"], cfg.get("database") or None


def connection_info() -> dict[str, str]:
    """Connection settings that are safe to show on screen (never the password)."""
    uri, username, _, database = _config()
    return {"uri": uri, "username": username, "database": database or "(home database)"}


@st.cache_resource(show_spinner=False)
def get_driver():
    """Create one thread-safe Neo4j Driver for the Streamlit process."""
    uri, username, password, _ = _config()
    driver = GraphDatabase.driver(uri, auth=(username, password))
    driver.verify_connectivity()
    return driver


def query(cypher: str, parameters: dict[str, Any] | None = None, *, write: bool = False) -> list[dict[str, Any]]:
    """Execute parameterized Cypher and return rows as dictionaries."""
    _, _, _, database = _config()
    records, _, _ = get_driver().execute_query(
        cypher,
        parameters_=parameters or {},
        database_=database,
        routing_=RoutingControl.WRITE if write else RoutingControl.READ,
    )
    return [record.data() for record in records]


def ping() -> bool:
    rows = query("RETURN 1 AS ok")
    return bool(rows and rows[0]["ok"] == 1)


def create_schema() -> None:
    statements = [
        "CREATE CONSTRAINT user_name_unique IF NOT EXISTS FOR (u:User) REQUIRE u.name IS UNIQUE",
        "CREATE CONSTRAINT fruit_name_unique IF NOT EXISTS FOR (f:Fruit) REQUIRE f.name IS UNIQUE",
    ]
    for stmt in statements:
        query(stmt, write=True)


def clear_data() -> None:
    """Delete every User and Fruit node with their relationships (other labels are left alone)."""
    query("MATCH (n) WHERE n:User OR n:Fruit DETACH DELETE n", write=True)


def seed_demo_data(*, reset: bool = False) -> None:
    """Load the notebook's sample dataset. MERGE makes it safe to run more than once.

    reset=True clears User/Fruit first, like the notebook does, so the result is exactly the sample data.
    """
    if reset:
        clear_data()
    create_schema()
    query("UNWIND $names AS name MERGE (u:User {name: name})", {"names": DEMO_USERS}, write=True)
    query("UNWIND $names AS name MERGE (f:Fruit {name: name})", {"names": DEMO_FRUITS}, write=True)
    query(
        """
        UNWIND $rows AS row
        MATCH (u:User {name: row[0]}), (f:Fruit {name: row[1]})
        MERGE (u)-[:LIKES]->(f)
        """,
        {"rows": DEMO_LIKES},
        write=True,
    )
    rebuild_similar()


# ---------- User ----------

def get_users() -> list[dict[str, Any]]:
    return query(
        """
        MATCH (u:User)
        OPTIONAL MATCH (u)-[:LIKES]->(f:Fruit)
        WITH u, count(DISTINCT f) AS likes
        OPTIONAL MATCH (u)-[:SIMILAR_TO]-(o:User)
        RETURN u.name AS name, likes, count(DISTINCT o) AS similar
        ORDER BY toLower(name), name
        """
    )


def create_user(name: str) -> bool:
    """Return False when the name is already taken."""
    rows = query(
        """
        OPTIONAL MATCH (x:User {name:$name})
        WITH x WHERE x IS NULL
        CREATE (u:User {name:$name})
        RETURN u.name AS name
        """,
        {"name": name},
        write=True,
    )
    return bool(rows)


def rename_user(name: str, new_name: str) -> bool:
    """Return False when the user is missing or `new_name` belongs to another user."""
    rows = query(
        """
        MATCH (u:User {name:$name})
        WHERE NOT EXISTS { MATCH (x:User {name:$new_name}) WHERE x <> u }
        SET u.name = $new_name
        RETURN u.name AS name
        """,
        {"name": name, "new_name": new_name},
        write=True,
    )
    return bool(rows)


def delete_user(name: str) -> bool:
    """DETACH DELETE: also removes the user's LIKES and SIMILAR_TO relationships."""
    rows = query(
        """
        MATCH (u:User {name:$name})
        DETACH DELETE u
        RETURN count(*) AS deleted
        """,
        {"name": name},
        write=True,
    )
    return bool(rows and rows[0]["deleted"])


# ---------- Fruit ----------

def get_fruits() -> list[dict[str, Any]]:
    return query(
        """
        MATCH (f:Fruit)
        OPTIONAL MATCH (u:User)-[:LIKES]->(f)
        RETURN f.name AS name, count(DISTINCT u) AS likes
        ORDER BY toLower(name), name
        """
    )


def create_fruit(name: str) -> bool:
    """Return False when the name is already taken."""
    rows = query(
        """
        OPTIONAL MATCH (x:Fruit {name:$name})
        WITH x WHERE x IS NULL
        CREATE (f:Fruit {name:$name})
        RETURN f.name AS name
        """,
        {"name": name},
        write=True,
    )
    return bool(rows)


def rename_fruit(name: str, new_name: str) -> bool:
    """Return False when the fruit is missing or `new_name` belongs to another fruit."""
    rows = query(
        """
        MATCH (f:Fruit {name:$name})
        WHERE NOT EXISTS { MATCH (x:Fruit {name:$new_name}) WHERE x <> f }
        SET f.name = $new_name
        RETURN f.name AS name
        """,
        {"name": name, "new_name": new_name},
        write=True,
    )
    return bool(rows)


def get_fruit_images() -> dict[str, bytes]:
    """Uploaded pictures keyed by fruit name; fruits without one are absent."""
    rows = query(
        """
        MATCH (f:Fruit)
        WHERE f.image IS NOT NULL
        RETURN f.name AS name, f.image AS image
        """
    )
    return {row["name"]: bytes(row["image"]) for row in rows}


def set_fruit_image(name: str, image: bytes | None) -> bool:
    """Store the picture as a byte-array property; None removes it (SET to null drops the property)."""
    rows = query(
        """
        MATCH (f:Fruit {name:$name})
        SET f.image = $image
        RETURN f.name AS name
        """,
        {"name": name, "image": image},
        write=True,
    )
    return bool(rows)


def delete_fruit(name: str) -> bool:
    """DETACH DELETE: also removes every LIKES relationship pointing at the fruit."""
    rows = query(
        """
        MATCH (f:Fruit {name:$name})
        DETACH DELETE f
        RETURN count(*) AS deleted
        """,
        {"name": name},
        write=True,
    )
    return bool(rows and rows[0]["deleted"])


# ---------- Relationships ----------

def list_likes() -> list[dict[str, Any]]:
    return query(
        """
        MATCH (u:User)-[:LIKES]->(f:Fruit)
        RETURN u.name AS user, f.name AS fruit
        ORDER BY toLower(user), user, toLower(fruit), fruit
        """
    )


def set_likes(user: str, fruits: list[str]) -> None:
    """Make the user's LIKES exactly `fruits`: drop the rest, add the missing."""
    params = {"user": user, "fruits": fruits}
    query(
        """
        MATCH (u:User {name:$user})-[r:LIKES]->(f:Fruit)
        WHERE NOT f.name IN $fruits
        DELETE r
        """,
        params,
        write=True,
    )
    query(
        """
        MATCH (u:User {name:$user})
        UNWIND $fruits AS fruit
        MATCH (f:Fruit {name: fruit})
        MERGE (u)-[:LIKES]->(f)
        """,
        params,
        write=True,
    )


def list_similarities() -> list[dict[str, Any]]:
    return query(
        """
        MATCH (a:User)-[:SIMILAR_TO]->(b:User)
        RETURN a.name AS user1, b.name AS user2
        ORDER BY toLower(user1), user1, toLower(user2), user2
        """
    )


def set_similar(user: str, others: list[str]) -> None:
    """Make the user's SIMILAR_TO neighbours exactly `others` (either direction)."""
    params = {"user": user, "others": others}
    query(
        """
        MATCH (a:User {name:$user})-[r:SIMILAR_TO]-(b:User)
        WHERE NOT b.name IN $others
        DELETE r
        """,
        params,
        write=True,
    )
    # Undirected MERGE: one SIMILAR_TO per pair, whichever direction already exists.
    query(
        """
        MATCH (a:User {name:$user})
        UNWIND $others AS other
        MATCH (b:User {name: other})
        WHERE a <> b
        MERGE (a)-[:SIMILAR_TO]-(b)
        """,
        params,
        write=True,
    )


def rebuild_similar() -> int:
    """Recreate every SIMILAR_TO from shared LIKES, as the notebook does; returns the number of pairs.

    Two users are similar when they like at least one fruit in common. Existing SIMILAR_TO
    relationships (including ones edited by hand) are replaced.
    """
    query("MATCH (:User)-[r:SIMILAR_TO]-(:User) DELETE r", write=True)
    query(
        """
        MATCH (u1:User)-[:LIKES]->(:Fruit)<-[:LIKES]-(u2:User)
        WHERE u1.name < u2.name
        MERGE (u1)-[:SIMILAR_TO]->(u2)
        """,
        write=True,
    )
    return query("MATCH (:User)-[r:SIMILAR_TO]->(:User) RETURN count(r) AS pairs")[0]["pairs"]


# ---------- Read models ----------

def get_dashboard_metrics() -> dict[str, int]:
    rows = query(
        """
        RETURN COUNT { (:User) } AS users,
               COUNT { (:Fruit) } AS fruits,
               COUNT { (:User)-[:LIKES]->(:Fruit) } AS likes,
               COUNT { (:User)-[:SIMILAR_TO]->(:User) } AS similarities
        """
    )
    return rows[0] if rows else {"users": 0, "fruits": 0, "likes": 0, "similarities": 0}


def get_profile(name: str) -> dict[str, Any] | None:
    """The user's liked fruit names and similar user names; None when the user does not exist."""
    rows = query(
        """
        MATCH (u:User {name:$name})
        RETURN u.name AS name,
               [(u)-[:LIKES]->(f:Fruit) | f.name] AS liked,
               [(u)-[:SIMILAR_TO]-(o:User) | o.name] AS similar
        """,
        {"name": name},
    )
    if not rows:
        return None
    row = rows[0]
    row["liked"] = sorted(set(row["liked"]), key=str.lower)
    row["similar"] = sorted(set(row["similar"]), key=str.lower)
    return row


def recommend_fruits(name: str, limit: int = 5) -> list[dict[str, Any]]:
    """Fruits liked by similar users that the user does not like yet.

    score = number of similar users who like the fruit.
    """
    return query(
        """
        MATCH (me:User {name:$name})
              -[:SIMILAR_TO]-(similar:User)
              -[:LIKES]->(fruit:Fruit)
        WHERE NOT EXISTS { MATCH (me)-[:LIKES]->(fruit) }
        WITH DISTINCT fruit, similar
        ORDER BY toLower(similar.name)
        RETURN fruit.name AS fruit,
               count(similar) AS score,
               collect(similar.name) AS similar_names
        ORDER BY score DESC, fruit
        LIMIT $limit
        """,
        {"name": name, "limit": int(limit)},
    )


def graph_neighborhood(name: str, depth: int = 1, types: list[str] | None = None) -> list[dict[str, Any]]:
    """Relationships reachable from the user within `depth` hops, following only `types`."""
    # Cypher cannot take the hop count as a parameter, so it is clamped to an int before formatting.
    depth = max(1, min(int(depth), 3))
    return query(
        f"""
        MATCH (u:User {{name:$name}})-[rels:LIKES|SIMILAR_TO*1..{depth}]-()
        WHERE all(rel IN rels WHERE type(rel) IN $types)
        UNWIND rels AS r
        WITH DISTINCT r
        RETURN startNode(r).name AS source, labels(startNode(r))[0] AS source_label,
               type(r) AS relationship,
               endNode(r).name AS target, labels(endNode(r))[0] AS target_label
        ORDER BY relationship, toLower(source), toLower(target)
        """,
        {"name": name, "types": types or RELATIONSHIP_TYPES},
    )
