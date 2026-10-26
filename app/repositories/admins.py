from pymysql.connections import Connection


def get_by_username(conn: Connection, username: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, username, password_hash, created_at FROM admins WHERE username = %s",
            (username,),
        )
        return cur.fetchone()


def upsert(conn: Connection, username: str, password_hash: str) -> str:
    """Create the admin, or reset its password if it exists. Returns 'created' or 'updated'."""
    existing = get_by_username(conn, username)
    with conn.cursor() as cur:
        if existing:
            cur.execute("UPDATE admins SET password_hash = %s WHERE id = %s", (password_hash, existing["id"]))
            result = "updated"
        else:
            cur.execute(
                "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
                (username, password_hash),
            )
            result = "created"
    conn.commit()
    return result
