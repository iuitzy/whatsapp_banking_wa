import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from app.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


def get_db_connection():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    logger.info("Database connection established")
    return conn


def execute_query(query: str, params: tuple = None) -> list:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        return results
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute_write(query: str, params: tuple = None) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Write failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_account_by_number(account_number: str) -> dict | None:
    results = execute_query(
        "SELECT * FROM accounts WHERE account_number = %s AND status = 'active'",
        (account_number,)
    )
    return results[0] if results else None


def get_transactions(account_id: int, limit: int = 5) -> list:
    return execute_query(
        """SELECT * FROM transactions
           WHERE account_id = %s
           ORDER BY created_at DESC
           LIMIT %s""",
        (account_id, limit)
    )
