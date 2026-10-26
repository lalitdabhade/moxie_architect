from datetime import datetime

from pymysql.connections import Connection


def create(conn: Connection, session_id: str, admin_id: int, csrf_token: str,
           now: datetime, expires_at: datetime) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM admin_sessions WHERE expires_at <= %s", (now,))
        cur.execute(
            "INSERT INTO admin_sessions (id, admin_id, csrf_token, created_at, expires_at) "
            "VALUES (%s, %s, %s, %s, %s)",
            (session_id, admin_id, csrf_token, now, expires_at),
        )
    conn.commit()


def get_valid(conn: Connection, session_id: str, now: datetime) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.id, s.csrf_token, s.expires_at, a.id AS admin_id, a.username "
            "FROM admin_sessions s JOIN admins a ON a.id = s.admin_id "
            "WHERE s.id = %s AND s.expires_at > %s",
            (session_id, now),
        )
        return cur.fetchone()


def delete(conn: Connection, session_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM admin_sessions WHERE id = %s", (session_id,))
    conn.commit()
