import sqlite3
import smtplib
from email.mime.text import MIMEText
import bcrypt
import base64
from typing import Optional
from datetime import datetime, timezone, timedelta
from .CONFIG.config import MAX_ATTEMPTS, LOCK_TIME_MINUTES,SMTP_MAIL, SMTP_PWD,DB_PATH

class USER_COL:
    UserId = 0
    RoleId = 1
    name = 2
    email = 3
    PasswordHash = 4
    PasswordSalt = 5
    token_v = 6
    ActivationCode = 7
    failed_attempts = 8
    locked_until = 9
    is_active = 10
    CreatedAt = 11
    UpdatedAt = 12


class Database:
    __db_is_connected = None

    fixed_salt = ""

    MAX_ATTEMPTS = MAX_ATTEMPTS
    LOCK_TIME_MINUTES = LOCK_TIME_MINUTES

    #added 21-DEC-2025
    @staticmethod
    def reset_no_of_failed_attempts(user_id):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE users
                SET failed_attempts = 0
                WHERE UserId = ?
                """,
                (user_id,)
            )
            conn.commit()

    @staticmethod
    def reset_login_attempts(user_id):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE users
                SET failed_attempts = 0, locked_until = NULL
                WHERE UserId = ?
                """,
                (user_id,)
            )
            conn.commit()


    @staticmethod
    def is_account_locked(user):
        locked_until = user[USER_COL.locked_until] #8
        if locked_until is None:
            return False

        lock_time = datetime.fromisoformat(locked_until)
        IST = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(IST)

        print("LOCK_TIME:", lock_time, lock_time.tzinfo)
        print("NOW:", datetime.now(IST))
        print("RESULT:", now < lock_time)


        return now < lock_time

    @staticmethod
    def handle_failed_login(email, failed_attempts):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            failed_attempts += 1
            IST = timezone(timedelta(hours=5, minutes=30))

            locked_until = None
            if failed_attempts >= Database.MAX_ATTEMPTS:
                locked_until = datetime.now(IST) + timedelta(minutes=Database.LOCK_TIME_MINUTES)

            cursor.execute(
                """
                UPDATE users
                SET failed_attempts = ?, locked_until = ?
                WHERE email = ?
                """,
                (failed_attempts, locked_until, email)
            )
            conn.commit()

    #dummy method, added - 16-DEC-2025
    @staticmethod
    def verification_code_operations(operation: str, code : str, email: Optional[str] = None):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}

        if operation =="update":
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print("verification_code_operations")
            cursor.execute(
                "UPDATE users SET ActivationCode = ? WHERE email = ?",
                (code, email)
            )
            conn.commit()
            
            if cursor.rowcount == 0:
                return False
            else:
                return True
        elif operation =="get":
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print("verification_code_operations")
            cursor.execute(
                "SELECT UserId, email FROM users WHERE ActivationCode = ?",
                (code,)
            )
            user = cursor.fetchone()

            if user == None:
                return False
            else:
                return user
        elif operation == "delete":
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print("verification_code_operations")
            cursor.execute(
                "UPDATE users SET ActivationCode = NULL WHERE email = ?",
                (email,)
            )
            conn.commit()

            if cursor.rowcount == 0:
                return False
            else:
                return True

    #dummy method, added - 16-DEC-2025
    @staticmethod
    def get_token_version(email):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print("get_token_version")
            cursor.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
            )
            conn.commit()
            user = cursor.fetchone()

            if user == None:
                return False
            else:
                return user[USER_COL.token_v] #6
        
    #dummy method, added - 16-DEC-2025
    @staticmethod
    def update_token_version(email,new_token_v):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print("get_token_version")
            cursor.execute(
                "UPDATE users SET token_v = ? WHERE email = ?",
                (new_token_v, email)
            )
            conn.commit()
            
            if cursor.rowcount == 0:
                return False
            else:
                return True

    #dummy method, added - 16-DEC-2025
    @staticmethod
    def update_user_and_token(id: str, password: str, token_v: str):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            print("update user, user_id = ", id)

            hashed_password = Database.Hash_password(password)
            print("salt", Database.fixed_salt)
            print("salt_length:", len(Database.fixed_salt))

            salt_b64 = base64.b64encode(Database.fixed_salt)          # ← bytes → bytes (base64 encoded)
            salt_b64_string = salt_b64.decode('utf-8')

            cursor.execute(
            "UPDATE users SET PasswordHash = ?, PasswordSalt = ?, token_v = ? WHERE UserId = ?",
            (hashed_password, salt_b64_string, token_v, id)
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE UserId = ?", (id,))
            return cursor.fetchone()

    @staticmethod
    def update_user(id: str, password: str):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            print("update user, user_id = ", id)

            hashed_password = Database.Hash_password(password)
            print("salt", Database.fixed_salt)
            print("salt_length:", len(Database.fixed_salt))

            salt_b64 = base64.b64encode(Database.fixed_salt)          # ← bytes → bytes (base64 encoded)
            salt_b64_string = salt_b64.decode('utf-8')

            cursor.execute(
            "UPDATE users SET PasswordHash = ?, PasswordSalt = ? WHERE UserId = ?",
            (hashed_password, salt_b64_string, id)
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE UserId = ?", (id,))
            return cursor.fetchone()

    @staticmethod
    def get_user(id: str):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            print("get_user, user_id = ", id)
            cursor.execute(
            "SELECT * FROM users WHERE UserId = ?", (id,)
            )
            conn.commit()
            return cursor.fetchone()

    @staticmethod
    def get_user_by_email(email: str):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            print("get_user, email = ", email)
            cursor.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
            )
            conn.commit()
            return cursor.fetchone()

    @staticmethod
    def get_user_id(email: str):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            print("get user - email = ", email)
            cursor.execute(
            "SELECT UserId FROM users WHERE email = ?", (email,)
            )
            conn.commit()
            row = cursor.fetchone()
            return row[0] if row else None

    @staticmethod
    def Hash_password(password: str):
        print("salt", Database.fixed_salt)
        return bcrypt.hashpw(password.encode(), Database.fixed_salt).decode()

    @classmethod
    def connect(cls):
        Database.fixed_salt = bcrypt.gensalt()
        cls.__db_is_connected = sqlite3.connect(DB_PATH, check_same_thread=False)
        cls.__db_is_connected.row_factory = sqlite3.Row
        return cls.__db_is_connected
    
    @staticmethod
    def check_user(email: str, password: str):

        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print(f"LOGIN: checking user in db")
            print(f"password = {password}, email = {email}")
            cursor.execute(

                "SELECT * FROM users WHERE email = ?",
                (email,)
            )
            user = cursor.fetchone()
            print("user:", user)

            re_hashed = ""
            stored_hash = ""
            if user:
                stored_hash = user[USER_COL.PasswordHash] #3
                salt_b64_string_from_db = user[USER_COL.PasswordSalt]  #4                 
                salt_bytes_recovered = base64.b64decode(salt_b64_string_from_db)

                re_hashed = bcrypt.hashpw(password.encode(), salt_bytes_recovered).decode()
                print("salt bytes recovered:", salt_bytes_recovered)
                print("stored salt length", len(salt_bytes_recovered))
                # print("stored_salt:", user[3])
                # print("stored_salt_length:",len(user[3]) )
                print("re_hashed:",re_hashed)
                print("stored_hash:",stored_hash)

            if user and re_hashed == stored_hash:
                print("password matched")
                return user
            else:
                return None
    
    @staticmethod
    def Create_user(name: str, email: str, password: str, is_active=0, RoleId=0):

        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            
            cursor.execute("SELECT UserId FROM users WHERE email = ?", (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                return None

            print("db is connected")

            hashed_password = Database.Hash_password(password)
            print("salt", Database.fixed_salt)
            print("salt_length:", len(Database.fixed_salt))

            salt_b64 = base64.b64encode(Database.fixed_salt)          # ← bytes → bytes (base64 encoded)
            salt_b64_string = salt_b64.decode('utf-8')

            cursor.execute(
            "INSERT INTO users (RoleID,name, email, PasswordHash, PasswordSalt ,is_active) VALUES (?,?, ?, ?, ?, ?)",
            (RoleId,name, email, hashed_password, salt_b64_string, is_active)
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            return cursor.fetchone()
    
    @staticmethod
    def send_activation_email(to_email, link):
        subject = "Activate your account"
        body = f"Click the link to activate your account:\n\n{link}"

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_MAIL
        msg['To'] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_MAIL, SMTP_PWD)
            server.send_message(msg)

    # added 17-Dec-2025
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

    @staticmethod
    def send_password_resetlink(to_email, link):
        subject = "change your password"
        body = f"Click the link to change your password:\n\n{link}"

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_MAIL
        msg['To'] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_MAIL, SMTP_PWD)
            server.send_message(msg)

    @staticmethod
    def activate_user(email):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print("user activated in db")
            cursor.execute("UPDATE users SET is_active=1 WHERE email=?", (email,))
            conn.commit()
            return cursor.rowcount

    @staticmethod
    def Is_user_Active(user_id,email):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print("checking user is_active in db")
            cursor.execute("SELECT is_active FROM users WHERE email =? AND UserId =?", (email,user_id))
            
            row = cursor.fetchone()
            if row is None:
                return None 
            return bool(row[USER_COL.is_active]) #0
            
    @staticmethod
    def Deactivate_user( email):
        """
        1. deactivate user
        """
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            print(" deactivate user in db")
            cursor.execute(
            "UPDATE users SET is_active = 0 WHERE email = ?",
            (email,)
            )
            conn.commit()
        return True
        

    @staticmethod
    def verify_JWT(user_id, email, JWT):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print("checking user is_active in db")
            cursor.execute("""
                SELECT 1
                FROM users
                WHERE email = ?
                AND UserId = ?
                AND JWT_Token = ?
                """,
                (email, user_id, JWT))
            conn.commit()
            return cursor.fetchone()
        
    @staticmethod
    def Save_JWT_Token(user_id, email, JWT, Expiry):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print("checking user is_active in db")
            cursor.execute(
                """
                UPDATE users
                SET JWT_Token = ?, Expiry_time = ?
                WHERE email = ?
                  AND UserId = ?
                """,
                (JWT, Expiry, email, user_id)
            )

            conn.commit()
            return cursor.rowcount > 0
        

    
