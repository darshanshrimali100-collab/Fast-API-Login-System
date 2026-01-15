from app.CORE.connection import master_connection
from typing import Generator

def init_userDB():
    with master_connection() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS S_Users (
                UserEmail TEXT PRIMARY KEY UNIQUE,
                RoleId INTEGER NOT NULL,
                DisplayName TEXT,
                PasswordHash TEXT,
                PasswordSalt BLOB,
                token_v INTEGER DEFAULT 0,
                ActivationCode TEXT,
                failed_attempts INTEGER DEFAULT 0,
                locked_until DATETIME DEFAULT NULL,
                is_active INTEGER DEFAULT 0,
                CreatedAt TEXT NOT NULL DEFAULT (datetime('now')),
                UpdatedAt TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        from app.AUTH.database import Database

        hash_password = Database.Hash_password("123456")

        salt = Database.fixed_salt

        result = cursor.execute(
            "SELECT 1 FROM S_Users WHERE UserEmail = ?",
            ("test@mail.com",)
        )

        if result.fetchone() is None:
            cursor.execute(
                """
                INSERT INTO S_Users
                (RoleId, DisplayName, UserEmail, PasswordHash, PasswordSalt)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("1", "AdminUser", "test@mail.com", hash_password, salt)
            )
            

def init_AdminDB():
    with master_connection() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS S_UserRoles (
                RoleId INTEGER PRIMARY KEY AUTOINCREMENT,
                RoleName TEXT NOT NULL UNIQUE,
                RoleDescription TEXT,
                CreatedAt TEXT NOT NULL DEFAULT (datetime('now')),
                UpdatedAt TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        result = cursor.execute(
            "SELECT 1 FROM S_UserRoles WHERE RoleName = ?",
            ("admin",)
        )

        if result.fetchone() is None:
            cursor.execute(
                "INSERT INTO S_UserRoles (RoleID, RoleName, RoleDescription) VALUES (?, ?, ?)",
                ("1", "admin", "System administrator with full access")
            )
            cursor.execute(
                "INSERT INTO S_UserRoles (RoleID, RoleName, RoleDescription) VALUES (?, ?, ?)",
                ("0", "user", "Normal user with limited access")
            )


def init_ProjectDB():
    with master_connection() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS S_Projects (
                ProjectId INTEGER PRIMARY KEY,
                UserEmail TEXT NOT NULL,
                ProjectName TEXT NOT NULL,
                ProjectStatus TEXT,
                CreatedAt TEXT NOT NULL DEFAULT (datetime('now')),
                UpdatedAt TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (UserEmail, ProjectName)
            )
        """)

        result = cursor.execute(
            """
            SELECT 1 FROM S_Projects
            WHERE UserEmail = ? AND ProjectName = ?
            """,
            ("test@mail.com", "Default Project")
        )

        if result.fetchone() is None:
            cursor.execute(
                "INSERT INTO S_Projects (UserEmail, ProjectName) VALUES (?, ?)",
                ("test@mail.com", "Default Project")
            )


def init_ErrorDB():
    with master_connection() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS S_UserErrors (
                MethodName TEXT NOT NULL,
                UserEmail TEXT,
                RequestBody TEXT,
                ErrorType TEXT,
                ErrorCode INTEGER NOT NULL,
                ErrorDetail TEXT
            )
        """)

def with_master_cursor() -> Generator:
    #try:
        with master_connection() as cursor:
            yield cursor
    #except Exception as e:
    #    # Unexpected DB error
    #    raise HTTPException(status_code=500, detail=str(e))
