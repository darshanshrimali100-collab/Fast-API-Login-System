from pydantic import BaseModel, EmailStr

class AdminRequest(BaseModel):
    Admin_email: EmailStr
    Admin_password: str

class User(BaseModel):
    username: str
    role: str

