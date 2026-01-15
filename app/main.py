"""
startup pe db se connect karna
"""

from fastapi import FastAPI
from app.AUTH.JWT_auth import router, signup_router
from app.AUTH.JWT_auth_new import new_router
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime, timezone, timedelta
from fastapi.staticfiles import StaticFiles
from .CONFIG.config import TEST_MODE, CORS_URL
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from app.ADMIN.admin import router as admin_router
from app.PROJECTS.projects import router as project_router
from fastapi import FastAPI, Request, HTTPException
from app.CORE.error_logger import ErrorLoggerDB
from app.CORE.utility import *
from app.CORE.DB import *
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR
from fastapi.responses import JSONResponse
import json
from app.CORE.connection import UserError

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
    app.include_router(project_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return await log_and_respond(
        request,
        "HTTP Error",
        exc.status_code,
        exc.detail,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return await log_and_respond(
        request,
        "Request Validation Error",
        HTTP_422_UNPROCESSABLE_ENTITY,
        #exc.errors(),
        json.dumps(exc.errors())
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # yahan tum DB errors, infra errors, bugs sab pakadte ho
    print("unhandeed exception")

    if exc.args and isinstance(exc.args[0], str):
        message =  exc.args[0]
    else:
        message = str(exc)

    return await log_and_respond(
        request,
        "Normal Exception",
        HTTP_500_INTERNAL_SERVER_ERROR,
        message
    )


async def log_and_respond(request: Request, ErrorType, status_code: int, detail):
    try:
        body = None
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.json()
            except:
                pass

        access_token = request.cookies.get("access_token")
        user_email = get_email_from_jwt(access_token) if access_token else None

        ErrorLoggerDB.log_error(
            method_name=f"{request.method} {request.url.path}",
            user_email=user_email,
            request_body=body,
            ErrorType=ErrorType,
            error_code=status_code,
            error_detail=detail,
        )
    except Exception as e:
        print("Error logger failed:", e)

    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )




# 1. DB CONNECT ON STARTUP
# -----------------------
@app.on_event("startup")
def startup_db():
    init_userDB()
    init_AdminDB()
    init_ProjectDB()
    init_ErrorDB()

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