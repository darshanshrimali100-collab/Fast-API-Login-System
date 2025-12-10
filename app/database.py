import sqlite3
import smtplib
from email.mime.text import MIMEText
import bcrypt
import base64

class Database:
    __db_is_connected = None

    fixed_salt = ""

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
            "UPDATE users SET password = ?, salt = ? WHERE id = ?",
            (hashed_password, salt_b64_string, id)
            )
            conn.commit()
            return True

    @staticmethod
    def get_user(id: str):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            print("get_user, user_id = ", id)
            cursor.execute(
            "SELECT * FROM users WHERE id = ?", (id,)
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
            "SELECT id FROM users WHERE email = ?", (email,)
            )
            conn.commit()
            return cursor.fetchone()[0]

    @staticmethod
    def Hash_password(password: str):
        print("salt", Database.fixed_salt)
        return bcrypt.hashpw(password.encode(), Database.fixed_salt).decode()

    @classmethod
    def connect(cls):
        Database.fixed_salt = bcrypt.gensalt()
        cls.__db_is_connected = sqlite3.connect("user.db", check_same_thread=False)
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

                "SELECT id, email, password, salt FROM users WHERE email = ?",
                (email,)
            )
            user = cursor.fetchone()
            print("user:", user)

            re_hashed = ""
            stored_hash = ""
            if user:
                stored_hash = user[2]
                salt_b64_string_from_db = user[3]                   
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
    def Create_user(name: str, email: str, password: str, is_active=0):

        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()
            
            print("db is connected")

            hashed_password = Database.Hash_password(password)
            print("salt", Database.fixed_salt)
            print("salt_length:", len(Database.fixed_salt))

            salt_b64 = base64.b64encode(Database.fixed_salt)          # ← bytes → bytes (base64 encoded)
            salt_b64_string = salt_b64.decode('utf-8')

            cursor.execute(
            "INSERT INTO users (name, email, password, salt ,is_active) VALUES (?, ?, ?, ?, ?)",
            (name, email, hashed_password, salt_b64_string, is_active)
            )
            conn.commit()
            return cursor.fetchone()
    
    @staticmethod
    def send_activation_email(to_email, link):
        subject = "Activate your account"
        body = f"Click the link to activate your account:\n\n{link}"

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = "darshanshrimali100@gmail.com"
        msg['To'] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("darshanshrimali100@gmail.com", "amxx vkxf isyl otso")
            server.send_message(msg)

    @staticmethod
    def send_password_resetlink(to_email, link):
        subject = "change your password"
        body = f"Click the link to change your password:\n\n{link}"

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = "darshanshrimali100@gmail.com"
        msg['To'] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("darshanshrimali100@gmail.com", "amxx vkxf isyl otso")
            server.send_message(msg)

    @staticmethod
    def activate_user(email):
        if Database.__db_is_connected == None:
            return {"message" : "db is not connected"}
        else:
            conn = Database.__db_is_connected
            cursor = conn.cursor()

            print("user activated in db")
            cursor.execute("UPDATE users SET is_active=1 WHERE email=? AND is_active=0", (email,))
            conn.commit()
            return cursor.rowcount > 0
        