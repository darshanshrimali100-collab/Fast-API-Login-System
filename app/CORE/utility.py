from app.AUTH.database import Database
from ..CONFIG.config import SECRET_KEY, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, SECURE_COOKIES
import jwt
from fastapi import HTTPException, Cookie, Depends, Response
from app.CORE.DB import with_master_cursor
from datetime import datetime, timezone, timedelta

ALGORITHM = "HS256"

def generate_token(token_v, email):
    """
    0. 
    1. handels logic for new_token 
    2. handels logic for refresh_token
    3. update token version in db
    4. embed new token version in JWT_token
    5. return jwt as response
    """
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": expire, "version": token_v}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

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


def get_current_user_email(response: Response, access_token: str = Cookie(None), cursor = Depends(with_master_cursor),):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")


    result = verify_user_jwt(access_token, cursor)
    
    #if result == "expired":
    #    print("*********************Cookie expired********************")
    #    email = get_email_from_jwt(jwt_token)
    #    token_v = Database.get_token_version(cursor, email)
    #    token_v += 1
    #    Database.update_token_version(cursor, email, token_v)

    #    # 6. Issue JWT
    #    jwt_token = generate_token(token_v, email)

    #    # Set token in response cookie
    #    response.set_cookie(
    #        key="access_token",
    #        value=jwt_token,
    #        httponly=True,
    #        secure=SECURE_COOKIES,
    #        samesite="lax",
    #        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    #        path="/",
    #    )
    #    print("***********************new cookie attached****************")
    #    email = get_email_from_jwt(jwt_token)
    #    return email

    if result is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = get_email_from_jwt(access_token)
    return email
