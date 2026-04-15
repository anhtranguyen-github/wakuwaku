import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from urllib.parse import urlparse
from app.core.config import settings

pool = None


def get_db_pool():
    """Get database connection pool"""
    global pool
    if pool is None:
        parsed = urlparse(settings.DATABASE_URL)
        pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/") or "postgres",
            user=parsed.username or "postgres",
            password=parsed.password or "postgres"
        )
    return pool


@contextmanager
def get_db_connection():
    """Get database connection context manager"""
    p = get_db_pool()
    conn = p.getconn()
    try:
        yield conn
    finally:
        p.putconn(conn)


def get_db_cursor():
    """Get database cursor for use with Depends"""
    p = get_db_pool()
    conn = p.getconn()
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
        p.putconn(conn)
