from fastapi import HTTPException, status, APIRouter, Body
from functools import wraps
from app.database import Database, USER_COL
from .database import Admin_database, USER_ROLE_COL
from app.ADMIN.models import *

def require_role(required_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            payload = kwargs.get("payload")

            if payload is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payload missing"
                )

            email = payload.Admin_email
            password = payload.Admin_password

            # 1️⃣ Authenticate user
            user = Database.check_user(email, password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )

            # 2️⃣ Get role
            role_id = user[USER_COL.RoleId]
            role = Admin_database.get_role_by_id(role_id)

            if not role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User role not found"
                )

            # 3️⃣ Role match
            if role[USER_ROLE_COL.RoleName] != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{required_role} role required"
                )

            return func(*args, **kwargs)
        
        return wrapper
    return decorator


router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/")
@require_role("admin")
def admin(payload: AdminRequest = Body(...), 
):
    return {"message": "Welcome Admin" }

