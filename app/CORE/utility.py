from app.AUTH.database import Database
from ..CONFIG.config import SECRET_KEY
import jwt
from fastapi import HTTPException, Cookie, Depends
from app.CORE.DB import with_master_cursor

ALGORITHM = "HS256"


def verify_user_jwt(token: str, cursor):
    """
    Verify a user's JWT against the server's secret key.

    Returns the payload (decoded JWT) if valid,
    or None if invalid/expired.
    """
    try:
        print("verifying JWT token")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("payload = ", payload)
        # added - 16-DEC-2025
        token_v = payload["version"]
        email = payload["sub"]
        print("user_token_v = ", token_v)
        print("email = ", email)
        token_v_db = Database.get_token_version(cursor, email)
        print("token_v_db = ", token_v_db)

        if not token_v:
            return False
        
        if token_v == token_v_db:
            return "verified"

        # get email from access_token
        # return payload  # payload contains user's data, e.g., {"sub": email, "exp": ...}
    
    except jwt.ExpiredSignatureError:
        return "expired"
    
    except jwt.InvalidTokenError:
        print("Invalid JWT")
        return None

def get_email_from_jwt(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload.get("sub")

    except jwt.ExpiredSignatureError:
        return None   # token expired

    except jwt.InvalidTokenError:
        return None   # invalid token


def get_current_user_email(access_token: str = Cookie(None), cursor = Depends(with_master_cursor),):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = verify_user_jwt(access_token, cursor)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = get_email_from_jwt(access_token)
    # user_id = Database.get_user_id(email)
    return email