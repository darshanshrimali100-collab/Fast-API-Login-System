from fastapi import APIRouter, HTTPException, Response, status, Request
from app.AUTH.database import Database
from ..CONFIG.config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, SECURE_COOKIES,MAX_ATTEMPTS
import jwt
from datetime import datetime, timezone, timedelta
import secrets
import string
from fastapi import Depends, Header
from fastapi import Query
from fastapi import Cookie
from app.AUTH.models import *
from app.CORE.utility import *
from app.PROJECTS.database import Projects_database
from app.CORE.DB import with_master_cursor

class USER_COL:
    email = 0
    RoleId = 1
    name = 2
    PasswordHash = 3
    PasswordSalt = 4
    token_v = 5
    ActivationCode = 6
    failed_attempts = 7
    locked_until = 8
    is_active = 9
    CreatedAt = 10
    UpdatedAt = 11

SECRET_KEY = SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES
SECURE = SECURE_COOKIES

new_router = APIRouter()

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
    
def generate_verification_code():
    print("generate_verification_code")
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(10))


# added 26-Dec-2025
def refresh_Token(token_v: str, email: str):
    """
    1. refresh token
    """
    print("refresh token, JWT auth")
    encoded_jwt = generate_token(token_v, email)

    if not encoded_jwt:
        return {"message": "failed to rotate token"}
    
    token_v = Database.get_token_version(email)
    new_token_v = token_v + 1
    result = Database.update_token_version(email, new_token_v)
    if result == None:
        return {"message" :"failed to update token_v in db"}
    
    encoded_jwt = generate_token(new_token_v, email)

    if not encoded_jwt:
        return {"message": "failed to rotate token"}

    return encoded_jwt


# Login/Logout

@new_router.post("/login")
def login(payload: LoginRequest, response: Response, cursor = Depends(with_master_cursor)):
    email = payload.email
    password = payload.password

    # 1. User existence check
    user = Database.get_user_by_email(cursor, email)
    if not user:
        raise HTTPException(
            status_code=485, #updated , 12-JAN-2026, Darshan Shrimali
            detail="Invalid credentials"
        )

    # 2. Account lock check
    if Database.is_account_locked(user):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account locked due to multiple failed attempts. Try again later."
        )

    # Reset attempts if lock expired
    if user[USER_COL.failed_attempts] >= MAX_ATTEMPTS:
        print("Lock expired, resetting failed attempts")
        Database.reset_no_of_failed_attempts(cursor, user[USER_COL.email])
        # update user
        user = Database.get_user_by_email(cursor, email)


    # 3. Password validation
    valid_user = Database.check_user(cursor, email, password)
    if not valid_user:
        Database.handle_failed_login(cursor, email, user[USER_COL.failed_attempts])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Password, failed attempt."
        )

    # 4. Reset failed attempts
    Database.reset_login_attempts(cursor, user[USER_COL.email])

    # 5. Token version logic
    token_v = Database.get_token_version(cursor, email)
    token_v += 1
    Database.update_token_version(cursor, email, token_v)

    # 6. Issue JWT
    jwt_token = generate_token(token_v, email)

    # 7. Set secure cookie
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=SECURE,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    Database.activate_user(cursor, email)

    return {
        "message": "Login successful",
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "name": user[USER_COL.name],
            "email": user[USER_COL.email]
        }
        }

@new_router.post("/logout")
def Logout(request: Request, response: Response, cursor = Depends(with_master_cursor)):
    jwt_token = request.cookies.get("access_token")
    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    try:
        # 2. Extract email from JWT
        email = get_email_from_jwt(jwt_token)  # Assume this returns email or raises
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    r = Database.Deactivate_user(cursor ,email)

    if r == None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to Logout user Now"
        )
    
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return {"message" : "User logged out Successfully"}
# 

# Signup

@new_router.post("/signup")
def signup(payload: SignupRequest, cursor = Depends(with_master_cursor)):
    name = payload.name
    email = payload.email
    password = payload.password

    # 1. Create user
    user = Database.Create_user(cursor, name, email, password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )

    # 2. Generate verification code
    code = generate_verification_code()
    saved = Database.verification_code_operations(cursor, "update", code, email)

    if not saved:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save verification code"
        )

    # 3. Send activation email
    #activation_link = f"http://localhost:8000/api/auth/activate?id={code}"
    #Database.send_activation_email(email, activation_link)

    subject = "activate your account"
    message = f"this is your activation code, do not share it = {code}"
    Database.send_email_with_message(email, message, subject)

    return {
        "message": "Signup successful. Activation link sent to email."
    }


@new_router.get("/activate")
def activate_account(response: Response, id: str = Query(...), cursor = Depends(with_master_cursor)):
    try:
        # 1. Validate verification code
        record = Database.verification_code_operations(cursor, "get", id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired activation code"
            )

        email = record[0]

        # added 12-JAN-2026, Darshan Shrimali
        # create new project "default", whenever new user is created.
        Projects_database.create_project(cursor, email, "default")
        result = Projects_database.set_project_status(cursor, email, "default","active")
        if result == None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="unable to open project now" # detail: Project not found or access denied
            )

        # 2. Delete verification code
        deleted = Database.verification_code_operations(cursor, "delete", id, email)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not clean verification code"
            )

        # 3. Token version logic
        token_v = Database.get_token_version(cursor, email)
        token_v += 1
        Database.update_token_version(cursor, email, token_v)

        # 4. Issue JWT
        jwt_token = generate_token(token_v, email)

        # 7. Set secure cookie
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            secure=SECURE,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )

        #added, 2-jan-2026
        Database.activate_user(cursor, email)

        return {
            "message": "Account activated successfully",
            "access_token": jwt_token,
            "token_type": "bearer"
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Activation token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid activation token"
        )

#

# Forgot password

@new_router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, cursor = Depends(with_master_cursor)):
    email = payload.email

    # Optional: user existence check (recommended)
    user = Database.get_user_by_email(cursor, email)
    if not user:
        return {
            "message": "If the email exists, a reset link has been sent"
        }

    # Generate reset code
    code = generate_verification_code()
    saved = Database.verification_code_operations(cursor, "update", code, email)

    if not saved:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate password reset link"
        )

    # reset_link = f"http://localhost:8000/api/auth/reset-password/verify?id={code}"
    # Database.send_password_resetlink(email, reset_link)

    subject = "Forgot password code"
    message = f"this is your Forgot password code, do not share it = {code}"
    Database.send_email_with_message(email, message, subject)

    return {
        "message": "If the email exists, a reset link has been sent"
    }

@new_router.get("/forgot-password/verify")
def verify_reset_code( id: str = Query(...), cursor = Depends(with_master_cursor)):
    record = Database.verification_code_operations(cursor, "get", id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )

    email = record[1]

    return {
        "message": "Reset code verified",
        "email": email,
        "reset_token": id
    }

@new_router.post("/reset-password")
def reset_password( payload: ResetPasswordRequest, cursor = Depends(with_master_cursor)):
    email = payload.email
    reset_token = payload.reset_token
    new_password = payload.new_password

    # 1. Verify reset token again (important)
    record = Database.verification_code_operations(cursor, "get", reset_token)
    if not record or record[0] != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )

    # commented, Darshan Shrimali, 8-Jan-2026
    # 2. Update password
    #user_id = Database.get_user_id(email)
    #if not user_id:
    #    raise HTTPException(
    #        status_code=status.HTTP_404_NOT_FOUND,
    #        detail="User not found"
    #    )

    updated = Database.update_user(cursor, email, new_password)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password update failed"
        )

    # 3. Delete reset token
    Database.verification_code_operations(cursor, "delete", reset_token, email)

    # 4. Invalidate old tokens
    token_v = Database.get_token_version(cursor, email)
    token_v += 1
    Database.update_token_version(cursor, email, token_v)

    # 5. Issue fresh JWT 
    jwt_token = generate_token(token_v, email)

    return {
        "message": "Password reset successful",
        "access_token": jwt_token,
        "token_type": "bearer"
    }

# added new 26-Dec-2025
@new_router.post("/reset-password/combined")
def reset_password_combined( response: Response, payload: ResetPasswordCombinedRequest, cursor = Depends(with_master_cursor)):
    reset_token = payload.reset_token
    new_password = payload.new_password

    # 1. Verify reset token
    record = Database.verification_code_operations(cursor, "get", reset_token)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )

    email = record[1]

    # commented, Darshan Shrimali, 8-Jan-2026
    # 2. Update password
    #user_id = Database.get_user_id(email)
    #if not user_id:
    #    raise HTTPException(
    #        status_code=status.HTTP_404_NOT_FOUND,
    #        detail="User not found"
    #    )

    updated = Database.update_user(cursor, email, new_password)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password update failed"
        )

    # 3. Delete reset token
    Database.verification_code_operations(cursor, "delete", reset_token, email)

    # 4. Invalidate old tokens
    token_v = Database.get_token_version(cursor, email)
    token_v += 1
    Database.update_token_version(cursor, email, token_v)

    # 5. Issue fresh JWT
    jwt_token = generate_token(token_v, email)

    response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            secure=SECURE,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )

    return {
        "message": "Password reset successful",
        "access_token": jwt_token,
        "token_type": "bearer"
    }

#

# Update password

@new_router.post("/password/update")
def change_password(
    response: Response,
    payload: ChangePasswordRequest,
    user=Depends(get_current_user_email),
    cursor = Depends(with_master_cursor)
):
    email = user
    print("payload = ", payload)
    # 1. Verify current password
    valid = Database.check_user(cursor, email, payload.current_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # commented, Darshan Shrimali, 8-Jan-2026
    # user_id = Database.get_user_id(email)
    # if not user_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="User not found"
    #     )

    # 2. Token version increment (invalidate old sessions)
    token_v = Database.get_token_version(cursor, email)
    token_v += 1

    # 3. Update password + token version
    updated = Database.update_user_and_token(
        cursor,
        email,
        payload.new_password,
        token_v
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password update failed"
        )

    # 4. Send confirmation email
    IST = timezone(timedelta(hours=5, minutes=30))
    subject = "Your Password Was Updated"
    message = f"Your password was updated successfully at {datetime.now(IST)}"
    Database.send_email_with_message(email, message, subject)

    # 5. Issue fresh JWT
    jwt_token = generate_token(token_v, email)

    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=SECURE,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return {
        "message": "Password changed successfully",
        "access_token": jwt_token,
        "token_type": "bearer"
    }

#

# user 

@new_router.post("/user")
def user_detail(request: Request, response: Response, cursor = Depends(with_master_cursor)):

    jwt_token = request.cookies.get("access_token")
    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    try:
        # 2. Extract email from JWT
        email = get_email_from_jwt(jwt_token)  # Assume this returns email or raises
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # 3. Get user details from DB
    user = Database.get_user_by_email(cursor, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    print("user = ", user[USER_COL.name])
    # 4. Return user details
    return {
            "name": user[USER_COL.name],
            "email": user[USER_COL.email],
            "LoggedIn": user[USER_COL.is_active],
            # Add other fields as required
        }
    


#