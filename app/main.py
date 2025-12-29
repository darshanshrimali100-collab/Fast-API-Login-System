"""
startup pe db se connect karna
"""

from fastapi import FastAPI
from app.JWT_auth import router, signup_router
from app.JWT_auth_new import new_router
from app.database import Database
from fastapi.responses import FileResponse
from datetime import datetime, timezone, timedelta
from fastapi.staticfiles import StaticFiles
from .config import TEST_MODE, CORS_URL
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

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

        if origin and origin != "http://localhost:3000":
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
            token_v INTEGER DEFAULT 0,
            code TEXT,
            failed_attempts INTEGER DEFAULT 0,
            locked_until DATETIME DEFAULT NULL,
            is_active INTEGER DEFAULT 0  
        )
    """)

    expiry_time = str(datetime.now(timezone.utc) + timedelta(minutes=30))

    # Insert sample user (only first time)
    cursor.execute("SELECT * FROM users WHERE email='test@mail.com'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            ("TestUser","test@mail.com", "123456",)
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

@app.get("/profile")
def forgot_password():
    return FileResponse("app/static/Profile.html")