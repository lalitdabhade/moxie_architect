"""Projects and their images. project_images.path holds a filename inside uploads/projects.

Write helpers do not commit; the caller commits once the whole operation (including file
writes) has succeeded, so a failure can roll back cleanly.
"""
from pymysql.connections import Connection


def _placeholders(n: int) -> str:
    return ", ".join(["%s"] * n)


def _attach_images(conn: Connection, projects: list[dict]) -> list[dict]:
    if not projects:
        return projects
    by_id = {p["id"]: p for p in projects}
    for p in projects:
        p["images"] = []
    ids = list(by_id)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id, project_id, path, sort_order FROM project_images "
            f"WHERE project_id IN ({_placeholders(len(ids))}) ORDER BY project_id, sort_order, id",
            ids,
        )
        for row in cur.fetchall():
            by_id[row["project_id"]]["images"].append(row)
    return projects


def list_projects(conn: Connection, section_id: int | None = None) -> list[dict]:
    sql = "SELECT id, section_id, title, created_at FROM projects"
    params: tuple = ()
    if section_id is not None:
        sql += " WHERE section_id = %s"
        params = (section_id,)
    sql += " ORDER BY created_at DESC, id DESC"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        projects = list(cur.fetchall())
    return _attach_images(conn, projects)


def get_project(conn: Connection, project_id: int, for_update: bool = False) -> dict | None:
    sql = "SELECT id, section_id, title, created_at FROM projects WHERE id = %s"
    if for_update:
        sql += " FOR UPDATE"
    with conn.cursor() as cur:
        cur.execute(sql, (project_id,))
        project = cur.fetchone()
    if project is None:
        return None
    return _attach_images(conn, [project])[0]


def count_by_section(conn: Connection) -> dict[int, int]:
    with conn.cursor() as cur:
        cur.execute("SELECT section_id, COUNT(*) AS n FROM projects GROUP BY section_id")
        return {row["section_id"]: row["n"] for row in cur.fetchall()}


def create_project(conn: Connection, section_id: int, title: str) -> int:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO projects (section_id, title) VALUES (%s, %s)", (section_id, title))
        return cur.lastrowid


def update_project(conn: Connection, project_id: int, section_id: int, title: str) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE projects SET section_id = %s, title = %s WHERE id = %s",
                    (section_id, title, project_id))


def delete_project(conn: Connection, project_id: int) -> list[str]:
    """Delete the project (images cascade). Returns image filenames to remove from disk."""
    with conn.cursor() as cur:
        cur.execute("SELECT path FROM project_images WHERE project_id = %s", (project_id,))
        paths = [row["path"] for row in cur.fetchall()]
        cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
    return paths


def next_sort_order(conn: Connection, project_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM project_images WHERE project_id = %s",
                    (project_id,))
        return cur.fetchone()["n"]


def add_image(conn: Connection, project_id: int, path: str, sort_order: int) -> int:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO project_images (project_id, path, sort_order) VALUES (%s, %s, %s)",
                    (project_id, path, sort_order))
        return cur.lastrowid


def delete_image(conn: Connection, project_id: int, image_id: int) -> str | None:
    """Returns the deleted image's filename, or None if it does not belong to the project."""
    with conn.cursor() as cur:
        cur.execute("SELECT path FROM project_images WHERE id = %s AND project_id = %s",
                    (image_id, project_id))
        row = cur.fetchone()
        if row is None:
            return None
        cur.execute("DELETE FROM project_images WHERE id = %s", (image_id,))
    return row["path"]


def reorder_images(conn: Connection, project_id: int, image_ids: list[int]) -> bool:
    """Apply a new order. image_ids must be exactly the project's image ids."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM project_images WHERE project_id = %s", (project_id,))
        current = {row["id"] for row in cur.fetchall()}
        if set(image_ids) != current or len(image_ids) != len(current):
            return False
        for position, image_id in enumerate(image_ids):
            cur.execute("UPDATE project_images SET sort_order = %s WHERE id = %s AND project_id = %s",
                        (position, image_id, project_id))
    return True
