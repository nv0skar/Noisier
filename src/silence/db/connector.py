from silence.__main__ import CONFIG

from pymysql import connect, OperationalError


def get_conn():
    _conn = CONFIG.get().db_conn
    try:
        return connect(
            host=_conn.host[0],
            port=_conn.host[1],
            user=_conn.username,
            password=_conn.password,
            database=_conn.db,
        )
    except OperationalError:
        raise Exception("Cannot establish connection to the database.")
