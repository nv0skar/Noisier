from silence.__main__ import CONFIG
from silence.db.dal import query
from silence.logging.default_logger import logger

from typing import List, Optional, Tuple

from msgspec import Struct, field


class TableField(Struct):
    name: str
    auto_increment: Optional[bool]


class TableSchema(Struct):
    name: str
    fields: List[TableField]
    primary_key_field: str
    is_view: bool


class DatabaseSchema(Struct):
    tables: List[TableSchema] = field(default_factory=list)

    @staticmethod
    def new_from_db():
        db_schema = DatabaseSchema()
        db_schema.load_tables()
        return db_schema

    def load_tables(self):
        res = query(q="SHOW FULL TABLES;")
        for table_data in res:
            (table_name, table_type) = [x for x in table_data.values()]
            (primary_key_field, fields) = self._get_table_fields(table_name)
            self.tables.append(
                TableSchema(table_name, fields, primary_key_field, table_type == "VIEW")
            )
        logger.debug(
            "Tables in the database: %s",
            self.tables,
        )

    # Returns the table's primary key and all the table's fields
    @staticmethod
    def _get_table_fields(table_name) -> Tuple[str, List[TableField]]:
        fields: List[TableField] = list()
        primary_key_field: str = str()
        for _field in query(f"SHOW COLUMNS FROM {table_name}"):
            if primary_key_field == "" and _field["Key"] == "PRI":
                primary_key_field = _field["Field"]
            fields.append(
                TableField(_field["Field"], _field["Extra"] == "auto_increment")
            )
        return (primary_key_field, fields)


# Caches the columns of a table, to avoid repetitive queries
global TABLE_COLUMNS
TABLE_COLUMNS = {}


def get_tables():
    res = query(q="SHOW FULL TABLES WHERE table_type = 'BASE TABLE';")
    tables = {}
    for table_data in res:
        # Grab the value that is not "BASE TABLE", which will be the name of the table
        table_name = next(x for x in table_data.values() if x != "BASE TABLE")
        tables[table_name] = get_table_fields(table_name)

    logger.debug("Tables in database: %s", str(tables))
    return tables


def get_views():
    res = query(q="SHOW FULL TABLES WHERE table_type = 'VIEW';")
    views = {}
    for view_data in res:
        # Grab the value that is not "VIEW", which will be the name of the view
        view_name = next(x for x in view_data.values() if x != "VIEW")
        views[view_name] = get_table_fields(view_name)

    logger.debug("Views in database: %s", str(views))
    return views


def get_primary_key(table_name):
    t_pure = next(t for t in get_tables() if t.lower() == table_name.lower())
    primary = query(f"SHOW KEYS FROM {t_pure} WHERE Key_name = 'PRIMARY'")

    if primary:
        return primary[0]["Column_name"]
    else:
        return None


def is_auto_increment(table_name, column_name):
    auto = query(
        f"SELECT EXTRA FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{CONFIG.get().db_conn.db}' AND TABLE_NAME = '{table_name}' AND COLUMN_NAME = '{column_name}'"
    )
    res = auto[0]["EXTRA"] == "auto_increment"
    return res


# Returns the list of names for the columns of a table, storing it
# after the first query for a given table
def get_table_fields(table_name) -> TableField:
    global TABLE_COLUMNS

    if table_name not in TABLE_COLUMNS:
        cols = query(f"SHOW COLUMNS FROM {table_name}")
        col_names = [col["Field"] for col in cols]
        TABLE_COLUMNS[table_name] = col_names
    return TABLE_COLUMNS[table_name]
