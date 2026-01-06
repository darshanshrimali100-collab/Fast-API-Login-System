import sqlite3
from app.CONFIG.config import DB_PATH

class USER_ROLE_COL:
    RoleId = 0
    RoleName = 1
    RoleDescription = 2
    CreatedAt = 3
    UpdatedAt = 4

class Admin_database:
    __Db_is_connected = None

    @classmethod
    def connect(cls):
       cls.__Db_is_connected = sqlite3.connect(DB_PATH, check_same_thread=False)
       return cls.__Db_is_connected

    @staticmethod
    def get_role_by_id(role_id):
        if Admin_database.__Db_is_connected is None:
            return {"message": "db is not connected"}
        else:
            conn = Admin_database.__Db_is_connected
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * 
                FROM S_UserRoles
                WHERE RoleId = ?
                """,
                (role_id,)
            )
            role = cursor.fetchone()
            print("user role = ", role)
            return role


