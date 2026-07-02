"""
커넥션 관리 모듈
- get_conn() : 커넥션 1개 반환
- close()    : 반환
- with 문 지원
"""
import pymysql
from db.config import DB_CONFIG


def get_conn() -> pymysql.connections.Connection:
    """pymysql 커넥션을 하나 열어서 반환한다."""
    return pymysql.connect(
        **DB_CONFIG,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


class DBSession:
    """
    with DBSession() as (conn, cur):
        cur.execute(...)
    """

    def __enter__(self):
        self.conn = get_conn()
        self.cur = self.conn.cursor()
        return self.conn, self.cur

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cur.close()
        self.conn.close()
        return False
