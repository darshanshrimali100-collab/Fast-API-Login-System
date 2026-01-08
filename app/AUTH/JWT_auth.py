"""
1. issue new token
2. refresh token
3. track token
"""

from fastapi import APIRouter
from fastapi import Form, Query
from app.AUTH.database import Database
import jwt
from datetime import datetime, timezone, timedelta
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi import Response
from fastapi import Request
from ..CONFIG.config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, SECURE_COOKIES
import secrets
import string

SECRET_KEY = SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES
SECURE = SECURE_COOKIES

Name = ""
Password = ""

router = APIRouter()
signup_router = APIRouter()

# dummy method, added - 16-DEC-2025
def generate_verification_code():
    print("generate_verification_code")
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(10))


# method, updated - 16-DEC-2025
def verify_user_jwt(token: str):
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
        token_v_db = Database.get_token_version(email)
        print("token_v_db = ", token_v_db)

        if not token_v:
            return False
        
        if token_v == token_v_db:
            return "verified"

        # return payload  # payload contains user's data, e.g., {"sub": email, "exp": ...}
    
    except jwt.ExpiredSignatureError:
        return "expired"
    
    except jwt.InvalidTokenError:
        print("Invalid JWT")
        return None


# dummy method, added - 16-DEC-2025
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
    
#dummy route, added - 16-DEC-2025
@signup_router.api_route("/update_password_successfull", methods=["GET","POST"])
def update_password_successfull(request: Request,new_password: str = Form(...)):
    print("/update_password")
    jwt = request.cookies.get("access_token")
    
    email = get_email_from_jwt(jwt)
    result =  verify_user_jwt(jwt)
    id = Database.get_user_id(email)

    if result == None:
        return {"message" : "invalid JWT_Token"}
    elif result == "expired":
        token_v = Database.get_token_version(email)
        r = Database.update_user_and_token(id, new_password, token_v)

        if r == None:
            return {"message":"password is not updated in db"}
        
        IST = timezone(timedelta(hours=5, minutes=30))
        subject = "Your Password Updated"
        message = f"your passward is updated successfully, time:{datetime.now(IST)}"
        Database.send_email_with_message(email,message, subject)

        response = refresh_Token(token_v, email,"/static/password_updated_successfully.html")
        return response        
    else:
        token_v = Database.get_token_version(email)
        r = Database.update_user_and_token(id, new_password, token_v)

        if r == None:
            return {"message":"password is not updated in db"}
        
        IST = timezone(timedelta(hours=5, minutes=30))
        subject = "Your Password Updated"
        message = f"your passward is updated successfully, time:{datetime.now(IST)}"
        Database.send_email_with_message(email,message, subject)

        response = refresh_Token(token_v,email,"/static/password_updated_successfully.html")
        return response

#dummy route, added - 16-DEC-2025
@signup_router.api_route("/update_password", methods=["GET","POST"])
def update_password(request: Request,Password: str = Form(...)):
    print("/update_password")
    jwt = request.cookies.get("access_token")
    
    email = get_email_from_jwt(jwt)
    user = Database.check_user(email, Password)

    if user == None:
        return {"message" : "your current password is wrong"}
    
    result =  verify_user_jwt(jwt)

    if result == None:
        return {"message" : "invalid JWT_Token"}
    elif result == "expired":
        token_v = Database.get_token_version(email)
        response = refresh_Token(token_v, email,"/static/update_password.html")
        return response        
    else:
        token_v = Database.get_token_version(email)
        response = issue_token(token_v,email,"/static/update_password.html")
        return response
    

#dummy route, added - 16-DEC-2025
@signup_router.api_route("/enter_current_password", methods=["GET","POST"])
def enter_current_password(request: Request):
    jwt = request.cookies.get("access_token")
    result = verify_user_jwt(jwt)

    response = RedirectResponse("/static/enter_current_password.html", status_code=303)

    if result == "expired":
        email = get_email_from_jwt(jwt)
        token_v = Database.get_token_version(email)
        response = refresh_Token(token_v,email,"/static/enter_current_password.html")
        return response
    elif result == None:
        return {"message" : "Invalid JWT"}
    else:
        return response


@signup_router.api_route("/home", methods=["GET", "POST"])
def home():
    with open("app/static/Home.html") as f:
        return HTMLResponse(f.read())

@router.post("/issue_token")
def issue_Token(response: Response, email: str = Form(...), password: str = Form(...)):
    """
    1. check if user is in db
    1. create new token
    2. and store in db
    """
    print("Login",email, password,)

    user1 = Database.get_user_by_email(email)

    if user1 == None:
        return {"message": "Invalid credentials"}
    
    if Database.is_account_locked(user1):
        return {
            "message": "Account locked due to multiple failed attempts. Try again after 1 minutes."
        }

    user = Database.check_user(email, password)
    print("Login: User = ", user)
    if(user == None):
        Database.handle_failed_login(email, user1[7])

        response = RedirectResponse("/static/login.html", status_code=303)
        response.delete_cookie("access_token", path="/")
        return response
    else:

        token_v = Database.get_token_version(email)
        if token_v == 0:
            print("issuing first JWT_token to user = ", email)
            Database.reset_login_attempts(user1[0])
            response = issue_token(token_v, email, "/static/Home.html")
            return response
        else:
            print("update token_v")
            Database.reset_login_attempts(user1[0])
            token_v = Database.get_token_version(email)
            response = refresh_Token(token_v,email,"/static/Home.html")
            return response

        
@signup_router.post("/issue_token")
def issue_Token(name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    print("signup route",email, password, name)

    Name = name
    Password = password

    user = Database.Create_user(Name, email, Password)
    user_id = Database.get_user_id(email)

    if user == None:
        return {"message" : f"user already exist, email = {email}"}

    code = generate_verification_code()
    result = Database.verification_code_operations("update", code, email)

    print("verification code = ", code)

    if result == False:
        return {"message" : "code cannot be saved in db right now"}
    
    activation_link = f"http://localhost:8000/Signup/activate?id={code}"
    Database.send_activation_email(email, activation_link)
    
    return {"message" : f"activation link sent to email = {email}"}

@signup_router.get("/activate")
def activate_account(response: Response, id: str = Query(...)):
    try:
        print("activate user_id = ", id)
        updated = Database.verification_code_operations("get", id)
    
        print("/activate ", updated)
        if updated:
            
            # added 5-DEC-2025
            email = updated[1]
            token_v = Database.get_token_version(email)
            
            result = Database.verification_code_operations("delete", id, email)

            if result == False:
                return {"message":"verification code not deleted from db"}

            response = issue_token(token_v, email, "/static/Home.html")
            return response
        else:
            response = RedirectResponse("/static/login.html", status_code=303)
            response.delete_cookie("access_token", path="/")
            return response

    except jwt.ExpiredSignatureError:
        return {"message": "Activation token expired."}
    except jwt.InvalidTokenError:
        return {"message": "Invalid activation token."}

@signup_router.post("/forgot_password")
def reset_password(email: str = Form(...)):
    print("forgot password")

    # user = Database.get_user_id(email)

    code = generate_verification_code()
    result = Database.verification_code_operations("update", code, email)

    print("verification code = ", code)
    
    if result == False:
        return {"message" : "code cannot be saved in db right now"}
    
    # if user == None:
    #     return {"message" : "no such user present"}
    
    reset_link = f"http://localhost:8000/Signup/reset_password?id={code}"
    Database.send_password_resetlink(email, reset_link)
    
    return {"message" : f"password reset link sent to email = {email}"}

@signup_router.get("/reset_password")
def reset_password_link(id: str = Query(...)):
    print("reset password")

    """
    1. check user id in db
    2. retrun reset_password page
    """
    print(f"reset_pasword, id = {id}")
    # user = Database.get_user(id)

    updated = Database.verification_code_operations("get", id)
    print("/activate ", updated)

    if updated == False:
        return {"message":"incorrect code"}
    
    email = updated[1]
    
    result = Database.verification_code_operations("delete", id, email)
                                                   
    if result == False:
        return {"message":"verification code not deleted from db"}

    return RedirectResponse(f"/static/Reset_password.html", status_code=303)

@signup_router.post("/change_password")
def Change_password(password: str = Form(...), email: str = Form(...)):
    """
    1. check user id
    2. if valid
        2.1 make new hash of pwd
        2.2 update new hash + its salt
    """
    print(f"change_password, user_email = {email}")
    user = Database.get_user_by_email(email)

    if user == None:
        return {"message":"invalid user email"}
    
    user = Database.get_user_id(email)

    if user == None:
        return {"message":"invalid user email"}

    user = Database.update_user(user, password)

    print(user)

    if user is None:
        return {"message":"failed to update password"}
    
    token_v = Database.get_token_version(email)

    response = refresh_Token(token_v,email, "/static/Home.html")
    return response

    
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


@signup_router.api_route("/profile", methods=["GET", "POST"])
def Profile(request: Request):
    """
    1. verify JWT.
    2. check user is active
    3. serve profile page
    """
    jwt = request.cookies.get("access_token")
    print(request.cookies)

    if not jwt:
        return {"error": "JWT missing"}

    result = verify_user_jwt(jwt)

    if result == "expired":
        email = get_email_from_jwt(jwt)
        token_v = Database.get_token_version(email)
        response = refresh_Token(token_v, email, "/static/Profile.html")
        return response
    elif result == None:
        return{"message" : "invalid JWT"}
    else:
        return RedirectResponse("/static/Profile.html", status_code=303)

@signup_router.get("/logout")
def Logout(request: Request, response: Response):
    """
    1. get user jwt
    2. get user email
    3. set user is_active = 0 where email = ?, (email,)
    4. return message - user logout successfull.
    """
    print("Logout Route")
    token = request.cookies.get("access_token")

    if not token:
        return {"message": "No active session"}

    email = get_email_from_jwt(token)
    user_id = Database.get_user_id(email)

    Database.Deactivate_user(user_id, email)

    response.delete_cookie("access_token", path="/")
    return {"message":"user logout successfull"}

def refresh_Token(token_v: str, email: str, redirect_url: str):
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

    response = RedirectResponse(redirect_url, status_code=303)
    response.set_cookie(
        key="access_token",
        value=encoded_jwt,
        httponly=True,
        secure=SECURE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

    return response

def issue_token(token_v, email, redirect_url: str):

    encoded_jwt = generate_token(token_v, email)

    if not encoded_jwt:
        return {"message": "failed to rotate token"}

    response = RedirectResponse(redirect_url, status_code=303)
    response.set_cookie(
        key="access_token",
        value=encoded_jwt,
        httponly=True,
        secure=SECURE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    return response

def Track_Tokens():
    """
    1. check if token is valid
        1.1 if valid Token:
            1.1.1 check expiry
                1.1.1.1 if expiry refresh token
            1.1.2 else
                1.1.2.1 redirect to correct resource
        1.2 else
            1.2.1 invalid token show error
    """
    pass