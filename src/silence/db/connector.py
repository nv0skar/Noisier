import pymysql

from silence.__main__ import CONFIG

#
# The connector fetches the relevant configuration parameters
# and uses them to build a connection to the database.
#


def get_conn():
    _conn = CONFIG.get().db_conn
    return pymysql.connect(
        host=_conn.host[0],
        port=_conn.host[1],
        user=_conn.username,
        password=_conn.password,
        database=_conn.db,
    )
