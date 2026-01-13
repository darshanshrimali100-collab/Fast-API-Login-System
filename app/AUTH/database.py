import smtplib
from email.mime.text import MIMEText
import bcrypt
from typing import Optional
from datetime import datetime, timezone, timedelta
from app.CORE.DB import with_master_cursor

from ..CONFIG.config import (
    MAX_ATTEMPTS,
    LOCK_TIME_MINUTES,
    SMTP_MAIL,
    SMTP_PWD,
)

from app.CORE.connection import master_connection


class USER_COL:
    UserEmail = 0
    RoleId = 1
    DisplayName = 2
    PasswordHash = 3
    PasswordSalt = 4
    token_v = 5
    ActivationCode = 6
    failed_attempts = 7
    locked_until = 8
    is_active = 9
    CreatedAt = 10
    UpdatedAt = 11


class Database:
    fixed_salt = bcrypt.gensalt()

    MAX_ATTEMPTS = MAX_ATTEMPTS
    LOCK_TIME_MINUTES = LOCK_TIME_MINUTES

    # =========================
    # Utils
    # =========================

    @staticmethod
    def Hash_password(password: str):
        return bcrypt.hashpw(password.encode(), Database.fixed_salt)

    # =========================
    # Login / Security
    # =========================

    @staticmethod
    def reset_no_of_failed_attempts(cursor, email):
        #with master_connection() as cursor:
            cursor.execute(
                """
                UPDATE S_Users
                SET failed_attempts = 0,
                    UpdatedAt = datetime('now')
                WHERE UserEmail = ?
                """,
                (email,),
            )

    @staticmethod
    def reset_login_attempts(cursor, email):
        #with master_connection() as cursor:
            cursor.execute(
                """
                UPDATE S_Users
                SET failed_attempts = 0,
                    locked_until = NULL,
                    UpdatedAt = datetime('now')
                WHERE UserEmail = ?
                """,
                (email,),
            )

    @staticmethod
    def is_account_locked(user):
        locked_until = user[USER_COL.locked_until]
        if locked_until is None:
            return False

        IST = timezone(timedelta(hours=5, minutes=30))
        return datetime.now(IST) < datetime.fromisoformat(locked_until)

    @staticmethod
    def handle_failed_login(cursor, email, failed_attempts):
        failed_attempts += 1
        locked_until = None

        if failed_attempts >= Database.MAX_ATTEMPTS:
            IST = timezone(timedelta(hours=5, minutes=30))
            locked_until = (
                datetime.now(IST)
                + timedelta(minutes=Database.LOCK_TIME_MINUTES)
            ).isoformat()

        #with master_connection() as cursor:
            cursor.execute(
                """
                UPDATE S_Users
                SET failed_attempts = ?,
                    locked_until = ?,
                    UpdatedAt = datetime('now')
                WHERE UserEmail = ?
                """,
                (failed_attempts, locked_until, email),
            )

    # =========================
    # Verification Code
    # =========================

    @staticmethod
    def verification_code_operations(cursor ,operation: str, code: str, email: Optional[str] = None):
        #with master_connection() as cursor:
            if operation == "update":
                cursor.execute(
                    """
                    UPDATE S_Users
                    SET ActivationCode = ?, UpdatedAt = datetime('now')
                    WHERE UserEmail = ?
                    """,
                    (code, email),
                )
                return cursor.rowcount() > 0

            elif operation == "get":
                return cursor.execute(
                    "SELECT UserEmail FROM S_Users WHERE ActivationCode = ?",
                    (code,),
                ).fetchone()

            elif operation == "delete":
                cursor.execute(
                    """
                    UPDATE S_Users
                    SET ActivationCode = NULL, UpdatedAt = datetime('now')
                    WHERE UserEmail = ?
                    """,
                    (email,),
                )
                return cursor.rowcount() > 0

    # =========================
    # Tokens
    # =========================

    @staticmethod
    def get_token_version(cursor ,email):
        #with master_connection() as cursor:
            row = cursor.execute(
                "SELECT token_v FROM S_Users WHERE UserEmail = ?",
                (email,),
            ).fetchone()
            return row[0] if row else None

    @staticmethod
    def update_token_version(cursor ,email, new_token_v):
        #with master_connection() as cursor:
            cursor.execute(
                """
                UPDATE S_Users
                SET token_v = ?, UpdatedAt = datetime('now')
                WHERE UserEmail = ?
                """,
                (new_token_v, email),
            )

    # =========================
    # Users
    # =========================

    @staticmethod
    def update_user_and_token(cursor ,email: str, password: str, token_v: int):
        hashed = Database.Hash_password(password)

        #with master_connection() as cursor:
        cursor.execute(
            """
            UPDATE S_Users
            SET PasswordHash = ?,
                PasswordSalt = ?,
                token_v = ?,
                UpdatedAt = datetime('now')
            WHERE UserEmail = ?
            """,
            (hashed, Database.fixed_salt, token_v, email),
        )
        return cursor.execute(
            "SELECT * FROM S_Users WHERE UserEmail = ?",
            (email,),
        ).fetchone()

    @staticmethod
    def update_user(cursor, email: str, password: str):
        hashed = Database.Hash_password(password)

        #with master_connection() as cursor:
        cursor.execute(
            """
            UPDATE S_Users
            SET PasswordHash = ?,
                PasswordSalt = ?,
                UpdatedAt = datetime('now')
            WHERE UserEmail = ?
            """,
            (hashed, Database.fixed_salt, email),
        )
        return cursor.execute(
            "SELECT * FROM S_Users WHERE UserEmail = ?",
            (email,),
        ).fetchone()

    @staticmethod
    def get_user_by_email(cursor, email):
        #with master_connection() as cursor:
            return cursor.execute(
                "SELECT * FROM S_Users WHERE UserEmail = ?",
                (email,),
            ).fetchone()

    @staticmethod
    def check_user(cursor ,email, password):
        #with master_connection() as cursor:
        user = cursor.execute(
            "SELECT * FROM S_Users WHERE UserEmail = ?",
            (email,),
        ).fetchone()

        if not user:
            return None

        
        re_hashed = bcrypt.hashpw(
            password.encode(),
            user[USER_COL.PasswordSalt],
        )

        return user if re_hashed == user[USER_COL.PasswordHash] else None

    @staticmethod
    def Create_user(cursor ,display_name, email, password, is_active=0, RoleId=0):
        hashed = Database.Hash_password(password)

        #with master_connection() as cursor:
        exists = cursor.execute(
            "SELECT 1 FROM S_Users WHERE UserEmail = ?",
            (email,),
        ).fetchone()
        if exists:
            return None
        cursor.execute(
            """
            INSERT INTO S_Users
            (UserEmail, RoleId, DisplayName, PasswordHash, PasswordSalt, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (email, RoleId, display_name, hashed, Database.fixed_salt, is_active),
        )
        return cursor.execute(
            "SELECT * FROM S_Users WHERE UserEmail = ?",
            (email,),
        ).fetchone()

    @staticmethod
    def activate_user(cursor, email):
        #with master_connection() as cursor:
            cursor.execute(
                """
                UPDATE S_Users
                SET is_active = 1, UpdatedAt = datetime('now')
                WHERE UserEmail = ?
                """,
                (email,),
            )

    @staticmethod
    def Is_user_Active(cursor ,email):
        #with master_connection() as cursor:
            row = cursor.execute(
                "SELECT is_active FROM S_Users WHERE UserEmail = ?",
                (email,),
            ).fetchone()
            return bool(row[0]) if row else None

    @staticmethod
    def Deactivate_user(cursor, email):
        #with master_connection() as cursor:
            cursor.execute(
                """
                UPDATE S_Users
                SET is_active = 0, UpdatedAt = datetime('now')
                WHERE UserEmail = ?
                """,
                (email,),
            ).fetchone()
            changes = cursor.execute("SELECT changes()").fetchone()[0]
            return changes > 0

    # =========================
    # Email
    # =========================

    @staticmethod
    def send_activation_email(to_email, link):
        Database.send_email_with_message(
            to_email,
            f"Click the link to activate your account:\n\n{link}",
            "Activate your account",
        )

    @staticmethod
    def send_password_resetlink(to_email, link):
        Database.send_email_with_message(
            to_email,
            f"Click the link to change your password:\n\n{link}",
            "Change your password",
        )

    @staticmethod
    def send_email_with_message(to_email, message, subject_str):
        msg = MIMEText(message)
        msg["Subject"] = subject_str
        msg["From"] = SMTP_MAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_MAIL, SMTP_PWD)
            server.send_message(msg)
