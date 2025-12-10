"""
1. issue new token
2. refresh token
3. track token
"""

from fastapi import APIRouter
from fastapi import Form, Query
from app.database import Database
import jwt
from datetime import datetime, timezone, timedelta
from fastapi.responses import FileResponse

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

Name = ""
Password = ""

router = APIRouter()
signup_router = APIRouter()

@router.post("/issue_token")
def issue_Token(email: str = Form(...), password: str = Form(...)):
    """
    1. check if user is in db
    1. create new token
    2. and store in db
    """

    print(email, password,)

    user = Database.check_user(email, password)
    print(user)
    if(user == None):
        # return {"message" : "no user found"}
        return FileResponse("app/static/Signup.html")
    else:
        # token isssue logic
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {"sub": email, "exp": expire}
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": encoded_jwt, "type": "bearer"}
        
@signup_router.post("/issue_token")
def issue_Token(name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    print("signup route",email, password, name)

    Name = name
    Password = password

    user = Database.Create_user(Name, email, Password)
    user_id = Database.get_user_id(email)

    activation_link = f"http://127.0.0.1:8000/Signup/activate?id={user_id}"
    Database.send_activation_email(email, activation_link)
    
    return {"message" : f"activation link sent to email = {email}"}

@signup_router.get("/activate")
def activate_account(id: str = Query(...)):
    try:
        print("activate user_id = ", id)
        user = Database.get_user(id)

        if user == None:
            return {"message":"invalid user id"}
        
        updated = Database.activate_user(user[2])

        if updated:
            return FileResponse("app/static/Home.html")
        else:
            return {"message": "User not found or already activated."}

    except jwt.ExpiredSignatureError:
        return {"message": "Activation token expired."}
    except jwt.InvalidTokenError:
        return {"message": "Invalid activation token."}

@signup_router.post("/forgot_password")
def reset_password(email: str = Form(...)):
    print("forgot password")

    user = Database.get_user_id(email)

    if user == None:
        return {"message" : "no such user present"}
    
    reset_link = f"http://127.0.0.1:8000/Signup/reset_password?id={user}"
    Database.send_password_resetlink(email, reset_link)
    
    return {"message" : f"password reset link sent to email = {email}"}

@signup_router.get("/reset_password")
def reset_password_link(id: str = Query(...)):
    print("reset password")

    """
    1. check user id in db
    2. retrun reset_password page
    """
    user = Database.get_user(id)

    if user == None:
        return {"message":"incorrect user id"}
    
    return FileResponse("app/static/Reset_password.html")

@signup_router.post("/change_password")
def Change_password( id: str = Form(...),password: str = Form(...)):
    """
    1. check user id
    2. if valid
        2.1 make new hash of pwd
        2.2 update new hash + its salt
    """

    user = Database.get_user(id)
    
    if user == None:
        return {"message":"invalid user id"}
    
    user = Database.update_user(id, password)

    if user == False:
        return {"message":"failed to update password"}
    
    return FileResponse("app/static/Home.html")


@router.get("/refresh_token")
def refresh_Token():
    """
    1. refresh token
    """
    pass

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