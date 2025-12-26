from enum import StrEnum


class SqlOps(StrEnum):
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    OTHER = "other"


# Returns the SQL operation for a given string
def get_sql_op(sql: str) -> SqlOps:
    first_token = sql.strip().split(" ")[0].lower()

    known_ops = {
        "select": SqlOps.SELECT,
        "insert": SqlOps.INSERT,
        "update": SqlOps.UPDATE,
        "delete": SqlOps.DELETE,
    }

    return known_ops.get(first_token, SqlOps.OTHER)
