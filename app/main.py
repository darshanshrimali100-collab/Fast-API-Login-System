"""
startup pe db se connect karna
"""

from fastapi import FastAPI
from app.AUTH.JWT_auth import router, signup_router
from app.AUTH.JWT_auth_new import new_router
from app.database import Database
from app.ADMIN.database import Admin_database
from fastapi.responses import FileResponse
from datetime import datetime, timezone, timedelta
from fastapi.staticfiles import StaticFiles
from .CONFIG.config import TEST_MODE, CORS_URL
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.ADMIN.admin import router as admin_router
import base64

app = FastAPI(title="Login")

print("cors url = ", CORS_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"test mode = {TEST_MODE}")

if TEST_MODE:
    # added 24-DEC-2025
    @app.middleware("http")
    async def browser_only_middleware(request: Request, call_next):

        # Allow docs & static
        if request.url.path in ["/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        ua = request.headers.get("user-agent", "")
        sec_fetch = request.headers.get("sec-fetch-site")
        origin = request.headers.get("origin")

        # Block non-browser tools
        if not sec_fetch:
            return JSONResponse(
                status_code=403,
                content={"detail": "Non-browser request blocked"}
            )

        if "Mozilla" not in ua:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid client"}
            )

        if origin and origin != CORS_URL:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid origin"}
            )

        return await call_next(request)


if TEST_MODE:
    app.mount(
        "/static",
        StaticFiles(directory="app/static"),
        name="static"
    )

    app.include_router(router, prefix="/Login")
    app.include_router(signup_router, prefix="/Signup")
else:
    app.include_router(new_router)
    app.include_router(admin_router)


def init_userDB():
    conn = Database.connect()
    cursor = conn.cursor()

    # Users table create if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            UserId INTEGER PRIMARY KEY AUTOINCREMENT,
            RoleId INTEGER NOT NULL,
            name TEXT,      
            email TEXT UNIQUE,
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

    hash_password = Database.Hash_password("123456")

    salt_b64 = base64.b64encode(Database.fixed_salt)          # ← bytes → bytes (base64 encoded)
    salt_b64_string = salt_b64.decode('utf-8')

    # Insert sample user (only first time)
    cursor.execute("SELECT * FROM users WHERE email='test@mail.com'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (RoleId,name, email, PasswordHash, PasswordSalt) VALUES (?, ?, ?, ?, ?)",
            ("1","AdminUser","test@mail.com", hash_password, salt_b64_string)
        )

    conn.commit()


def init_AdminDB():
    conn = Admin_database.connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS S_UserRoles (
            RoleId INTEGER PRIMARY KEY AUTOINCREMENT,
            RoleName TEXT NOT NULL UNIQUE,
            RoleDescription TEXT,
            CreatedAt TEXT NOT NULL DEFAULT (datetime('now')),
            UpdatedAt TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # insert admin role only once
    cursor.execute(
        "SELECT RoleId FROM S_UserRoles WHERE RoleName = ?",
        ("admin",)
    )

    if not cursor.fetchone():
        cursor.execute(
            """
            INSERT INTO S_UserRoles (RoleID, RoleName, RoleDescription)
            VALUES (?, ?, ?)
            """,
            ("1", "admin", "System administrator with full access")
        )
        cursor.execute(
            """
            INSERT INTO S_UserRoles (RoleID, RoleName, RoleDescription)
            VALUES (?, ?, ?)
            """,
            ("0","user", "Normal user with limited access")
        )

    conn.commit()



# 1. DB CONNECT ON STARTUP
# -----------------------
@app.on_event("startup")
def startup_db():
    init_userDB()
    init_AdminDB()

@app.get("/")
def Login():
    return FileResponse("app/static/login.html")

@app.get("/signup")
def Signup():
    return FileResponse("app/static/Signup.html")

@app.get("/forgot_password")
def forgot_password():
    return FileResponse("app/static/Forgot_password.html")

@app.get("/profile")
def forgot_password():
    return FileResponse("app/static/Profile.html")