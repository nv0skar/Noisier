from silence.db.dal import query
from silence.logging.default_logger import logger

from typing import List, Optional, Tuple

from msgspec import Struct, field


class TableField(Struct, frozen=True, gc=False, forbid_unknown_fields=True):
    name: str
    auto_increment: Optional[bool]


class TableSchema(Struct, frozen=True, gc=False, forbid_unknown_fields=True):
    name: str
    fields: List[TableField]
    primary_key_field: str
    is_view: bool


class DatabaseSchema(Struct, gc=False, forbid_unknown_fields=True):
    tables: List[TableSchema] = field(default_factory=list)

    @staticmethod
    def new_from_db():
        db_schema = DatabaseSchema()
        db_schema.load_tables()
        return db_schema

    """
    This method is only valid when the 'Self.table' field hasn't been
    modified after it's initial load
    """

    def get_table(self, table_name: str) -> Optional[TableSchema]:
        return next(
            (table for table in DATABASE_SCHEMA.tables if table.name == table_name),
            None,
        )

    def load_tables(self):
        if len(self.tables) != 0:
            raise Exception(
                "Cannot overwrite alrady loaded database's schema on runtime!"
            )
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


DATABASE_SCHEMA = DatabaseSchema()
