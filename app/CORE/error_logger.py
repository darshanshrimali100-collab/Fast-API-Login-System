
from app.AUTH.database import Database
import json
import sqlite3
from ..CONFIG.config import DB_PATH
from app.CORE.connection import master_connection

class ErrorLoggerDB:

    __db_is_connected = None

    @classmethod
    def connect(cls):
        cls.__db_is_connected = sqlite3.connect(DB_PATH, check_same_thread=False)
        return cls.__db_is_connected

    @classmethod
    def log_error(cls, method_name: str, user_email: str | None, request_body: dict | None, error_code: int, error_detail: str):
        """
        Insert an error log into S_UserErrors table.
        """
        try:
            if error_code != 485:
                with master_connection() as cursor:
                    cursor.execute("""
                        INSERT INTO S_UserErrors (MethodName, UserEmail, RequestBody, ErrorCode, ErrorDetail)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        method_name,
                        user_email,
                        json.dumps(request_body) if request_body else None,
                        error_code,
                        error_detail
                    ))
        except Exception as e:
            print("Failed to log error:", e)
