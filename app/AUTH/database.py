import sqlite3
import smtplib
from email.mime.text import MIMEText
import bcrypt
import base64
from typing import Optional
from datetime import datetime, timezone, timedelta
from ..CONFIG.config import MAX_ATTEMPTS, LOCK_TIME_MINUTES, SMTP_MAIL, SMTP_PWD, DB_PATH


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
    __db_is_connected = None
    fixed_salt = b""

    MAX_ATTEMPTS = MAX_ATTEMPTS
    LOCK_TIME_MINUTES = LOCK_TIME_MINUTES

    @classmethod
    def connect(cls):
        cls.fixed_salt = bcrypt.gensalt()
        cls.__db_is_connected = sqlite3.connect(DB_PATH, check_same_thread=False)
        cls.__db_is_connected.row_factory = sqlite3.Row
        return cls.__db_is_connected

    @staticmethod
    def Hash_password(password: str):
        return bcrypt.hashpw(password.encode(), Database.fixed_salt)

    @staticmethod
    def reset_no_of_failed_attempts(email):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            """
            UPDATE S_Users
            SET failed_attempts = 0,
                UpdatedAt = datetime('now')
            WHERE UserEmail = ?
            """,
            (email,)
        )
        Database.__db_is_connected.commit()

    @staticmethod
    def reset_login_attempts(email):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            """
            UPDATE S_Users
            SET failed_attempts = 0,
                locked_until = NULL,
                UpdatedAt = datetime('now')
            WHERE UserEmail = ?
            """,
            (email,)
        )
        Database.__db_is_connected.commit()

    @staticmethod
    def is_account_locked(user):
        locked_until = user[USER_COL.locked_until]
        if locked_until is None:
            return False

        IST = timezone(timedelta(hours=5, minutes=30))
        return datetime.now(IST) < datetime.fromisoformat(locked_until)

    @staticmethod
    def handle_failed_login(email, failed_attempts):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        failed_attempts += 1
        locked_until = None

        if failed_attempts >= Database.MAX_ATTEMPTS:
            IST = timezone(timedelta(hours=5, minutes=30))
            locked_until = (
                datetime.now(IST)
                + timedelta(minutes=Database.LOCK_TIME_MINUTES)
            ).isoformat()

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            """
            UPDATE S_Users
            SET failed_attempts = ?,
                locked_until = ?,
                UpdatedAt = datetime('now')
            WHERE UserEmail = ?
            """,
            (failed_attempts, locked_until, email)
        )
        Database.__db_is_connected.commit()

    @staticmethod
    def verification_code_operations(operation: str, code: str, email: Optional[str] = None):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()

        if operation == "update":
            cursor.execute(
                """
                UPDATE S_Users
                SET ActivationCode = ?, UpdatedAt = datetime('now')
                WHERE UserEmail = ?
                """,
                (code, email)
            )

        elif operation == "get":
            cursor.execute(
                "SELECT UserEmail FROM S_Users WHERE ActivationCode = ?",
                (code,)
            )
            return cursor.fetchone()

        elif operation == "delete":
            cursor.execute(
                """
                UPDATE S_Users
                SET ActivationCode = NULL, UpdatedAt = datetime('now')
                WHERE UserEmail = ?
                """,
                (email,)
            )

        Database.__db_is_connected.commit()
        return cursor.rowcount > 0

    @staticmethod
    def get_token_version(email):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            "SELECT token_v FROM S_Users WHERE UserEmail = ?",
            (email,)
        )
        row = cursor.fetchone()
        return row["token_v"] if row else None

    @staticmethod
    def update_token_version(email, new_token_v):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            """
            UPDATE S_Users
            SET token_v = ?, UpdatedAt = datetime('now')
            WHERE UserEmail = ?
            """,
            (new_token_v, email)
        )
        Database.__db_is_connected.commit()
        return cursor.rowcount > 0

    @staticmethod
    def update_user_and_token(email: str, password: str, token_v: int):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        hashed_password = Database.Hash_password(password)

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            """
            UPDATE S_Users
            SET PasswordHash = ?,
                PasswordSalt = ?,
                token_v = ?,
                UpdatedAt = datetime('now')
            WHERE UserEmail = ?
            """,
            (hashed_password, Database.fixed_salt, token_v, email)
        )
        Database.__db_is_connected.commit()

        cursor.execute("SELECT * FROM S_Users WHERE UserEmail = ?", (email,))
        return cursor.fetchone()

    @staticmethod
    def update_user(email: str, password: str):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        hashed_password = Database.Hash_password(password)

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            """
            UPDATE S_Users
            SET PasswordHash = ?,
                PasswordSalt = ?,
                UpdatedAt = datetime('now')
            WHERE UserEmail = ?
            """,
            (hashed_password, Database.fixed_salt, email)
        )
        Database.__db_is_connected.commit()

        cursor.execute("SELECT * FROM S_Users WHERE UserEmail = ?", (email,))
        return cursor.fetchone()

    @staticmethod
    def get_user_by_email(email: str):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()
        cursor.execute("SELECT * FROM S_Users WHERE UserEmail = ?", (email,))
        return cursor.fetchone()

    @staticmethod
    def check_user(email: str, password: str):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()
        cursor.execute("SELECT * FROM S_Users WHERE UserEmail = ?", (email,))
        user = cursor.fetchone()
        if not user:
            return None

        re_hashed = bcrypt.hashpw(
            password.encode(),
            user[USER_COL.PasswordSalt]
        )

        return user if re_hashed == user[USER_COL.PasswordHash] else None

    @staticmethod
    def Create_user(display_name: str, email: str, password: str, is_active=0, RoleId=0):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            "SELECT 1 FROM S_Users WHERE UserEmail = ?",
            (email,)
        )
        if cursor.fetchone():
            return None

        hashed_password = Database.Hash_password(password)

        cursor.execute(
            """
            INSERT INTO S_Users
            (UserEmail, RoleId, DisplayName, PasswordHash, PasswordSalt, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (email, RoleId, display_name, hashed_password, Database.fixed_salt, is_active)
        )
        Database.__db_is_connected.commit()

        cursor.execute("SELECT * FROM S_Users WHERE UserEmail = ?", (email,))
        return cursor.fetchone()

    @staticmethod
    def activate_user(email):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            """
            UPDATE S_Users
            SET is_active = 1, UpdatedAt = datetime('now')
            WHERE UserEmail = ?
            """,
            (email,)
        )
        Database.__db_is_connected.commit()
        return cursor.rowcount > 0

    @staticmethod
    def Is_user_Active(email):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            "SELECT is_active FROM S_Users WHERE UserEmail = ?",
            (email,)
        )
        row = cursor.fetchone()
        return bool(row["is_active"]) if row else None

    @staticmethod
    def Deactivate_user(email):
        if Database.__db_is_connected is None:
            return {"message": "db is not connected"}

        cursor = Database.__db_is_connected.cursor()
        cursor.execute(
            """
            UPDATE S_Users
            SET is_active = 0, UpdatedAt = datetime('now')
            WHERE UserEmail = ?
            """,
            (email,)
        )
        Database.__db_is_connected.commit()
        return True

    @staticmethod
    def send_activation_email(to_email, link):
        msg = MIMEText(f"Click the link to activate your account:\n\n{link}")
        msg["Subject"] = "Activate your account"
        msg["From"] = SMTP_MAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_MAIL, SMTP_PWD)
            server.send_message(msg)

    @staticmethod
    def send_password_resetlink(to_email, link):
        msg = MIMEText(f"Click the link to change your password:\n\n{link}")
        msg["Subject"] = "Change your password"
        msg["From"] = SMTP_MAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_MAIL, SMTP_PWD)
            server.send_message(msg)


    @staticmethod
    def send_email_with_message(to_email, message, subject_str):
        subject = subject_str
        body = f"{message}"

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_MAIL
        msg['To'] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_MAIL, SMTP_PWD)
            server.send_message(msg)
