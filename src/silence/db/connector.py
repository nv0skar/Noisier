import pymysql

from silence.__main__ import CONFIG

#
# The connector fetches the relevant configuration parameters
# and uses them to build a connection to the database.
#


def get_conn():
    return pymysql.connect(
        host=CONFIG.DB_CONN["host"],
        port=CONFIG.DB_CONN["port"],
        user=CONFIG.DB_CONN["username"],
        password=CONFIG.DB_CONN["password"],
        database=CONFIG.DB_CONN["database"],
    )
