"""Inquiries. layout_file_path holds a randomized filename inside uploads/layouts."""
from pymysql.connections import Connection

_COLUMNS = ("id, name, mobile, email, address, service_type, house_type, house_type_other, area_sqft, "
            "layout_file_path, layout_original_name, budget_range, created_at")


def create(conn: Connection, data: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO inquiries (name, mobile, email, address, service_type, house_type, house_type_other, "
            "area_sqft, layout_file_path, layout_original_name, budget_range) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (data["name"], data["mobile"], data["email"], data["address"], data["service_type"],
             data["house_type"], data["house_type_other"], data["area_sqft"],
             data.get("layout_file_path"), data.get("layout_original_name"), data["budget_range"]),
        )
        return cur.lastrowid


def list_page(conn: Connection, service_type: str | None, limit: int, offset: int) -> list[dict]:
    sql = f"SELECT {_COLUMNS} FROM inquiries"
    params: list = []
    if service_type:
        sql += " WHERE service_type = %s"
        params.append(service_type)
    sql += " ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s"
    params += [limit, offset]
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def count_by_service(conn: Connection) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute("SELECT service_type, COUNT(*) AS n FROM inquiries GROUP BY service_type")
        return {row["service_type"]: row["n"] for row in cur.fetchall()}


def get(conn: Connection, inquiry_id: int) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(f"SELECT {_COLUMNS} FROM inquiries WHERE id = %s", (inquiry_id,))
        return cur.fetchone()


def delete(conn: Connection, inquiry_id: int) -> str | None:
    """Delete the inquiry (caller commits). Returns its layout filename, if any."""
    with conn.cursor() as cur:
        cur.execute("SELECT layout_file_path FROM inquiries WHERE id = %s", (inquiry_id,))
        row = cur.fetchone()
        cur.execute("DELETE FROM inquiries WHERE id = %s", (inquiry_id,))
    return row["layout_file_path"] if row else None
