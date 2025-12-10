"""
startup pe db se connect karna
"""

from fastapi import FastAPI
from app.JWT_auth import router, signup_router
from app.database import Database
from fastapi.responses import FileResponse

app = FastAPI(title="Login")

app.include_router(router, prefix="/Login")
app.include_router(signup_router, prefix="/Signup")

# 1. DB CONNECT ON STARTUP
# -----------------------
@app.on_event("startup")
def startup_db():
    conn = Database.connect()
    cursor = conn.cursor()

    # Users table create if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,      
            email TEXT UNIQUE,
            password TEXT,
            salt BLOB,
            is_active INTEGER DEFAULT 0  
        )
    """)

    # Insert sample user (only first time)
    cursor.execute("SELECT * FROM users WHERE email='test@mail.com'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            ("TestUser","test@mail.com", "123456")
        )

    conn.commit()

@app.get("/")
def Login():
    return FileResponse("app/static/login.html")

@app.get("/signup")
def Signup():
    return FileResponse("app/static/Signup.html")

@app.get("/forgot_password")
def forgot_password():
    return FileResponse("app/static/Forgot_password.html")