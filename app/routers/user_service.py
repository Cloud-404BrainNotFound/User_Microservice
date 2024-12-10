from fastapi import APIRouter, Depends, HTTPException,Form
from sqlalchemy.orm import Session
from app.models.user import User
from app.database import get_db
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import enum
import smtplib
from google.oauth2 import id_token
from google.auth.transport import requests
import jwt
from dotenv import load_dotenv
import os

load_dotenv()

user_router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXPIRE_MINUTES = int(os.getenv('JWT_EXPIRE_MINUTES', '30'))
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')

class UserRole(enum.Enum):
    CUSTOMER = "customer"
    MERCHANT = "merchant"

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str
    store_id: Optional[str] = None

class GoogleToken(BaseModel):
    google_token: str

@user_router.get("/first_user")
def get_first_user_id(db: Session = Depends(get_db)):
    first_user = db.query(User).first()

    if not first_user:
        raise HTTPException(status_code=404, detail="No user found")
    return {"id": first_user.id}

@user_router.get("/{username}")
def get_user(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.id, "username": user.username, "email": user.email}

@user_router.post("/login/email")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        # 用户不存在
        raise HTTPException(status_code=404, detail="User not found")
    elif (password is None) or (user.password != password):
        # 密码不匹配
        raise HTTPException(status_code=401, detail="Incorrect password")
    else:
        access_token = create_access_token(user)
        # 登录成功
        return {
            "message": "Login successful", 
            "access_token": access_token,
            "user_id": user.id, 
            "email": user.email}

@user_router.post("/login/google")
async def google_login(credentials: dict, db: Session = Depends(get_db)):
    try:
        # 验证Google Token
        token = credentials.get('google_token')
        if not token:
            raise HTTPException(status_code=400, detail="Missing google_token")
            
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        email = idinfo['email']
        # 检查用户是否存在
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # 如果用户不存在，创建新用户
            new_user = User(
                username=idinfo.get('name', email.split('@')[0]),
                email=email,
                password="GOOGLE_AUTH",  # Google登录的用户不需要密码 但因为数据库不允许密码为null 创建一个默认密码标记
                role=UserRole.CUSTOMER.value,  # 默认为客户角色
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user
            
            # 发送欢迎邮件
            try:
                send_signup_email_gmail(user.email, user.username)
            except Exception as e:
                print(f"Failed to send welcome email: {e}")
        
        # 创建访问令牌
        access_token = create_access_token(user)
        return {
            "message": "Login successful",
            "user_id": user.id,
            "email": user.email,
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")

@user_router.post("/signup")
def add_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # 检查用户是否已存在（通过 email）
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered")

    # 创建新用户
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,  # 将来应该哈希处理密码
        role=user_data.role,
        store_id=user_data.store_id,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    # 将新用户添加到数据库
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # 刷新以获取新用户的完整信息
    try:
        send_signup_email_gmail(new_user.email, new_user.username)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send signup email: {str(e)}")

    return {"message": "User created successfully", "user_id": new_user.id, "username": new_user.username, "email": new_user.email}

def create_access_token(user: User) -> str:
    """创建JWT访问令牌"""
    expires_delta = timedelta(minutes=JWT_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    
    user_role = user.role
    if hasattr(user_role, 'value'):  # 如果是枚举类型
        user_role = user_role.value

    to_encode = {
        "sub": str(user.id),
        "email": user.email,
        "role": user_role,
        "exp": expire
    }
    
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def send_signup_email_gmail(recipient_email: str, username: str):
    sender_email = "zhngyiyan@gmail.com"
    sender_password = "btzl rxxu opoe cwoh"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    # 创建邮件内容
    subject = "Welcome to Our Service!"
    body = f"""
    Hi {username},

    Thank you for signing up for our service! We're excited to have you on board.

    Best regards,
    The Team
    """
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # 连接到 SMTP 服务器并发送邮件
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # 启用 TLS 加密
            server.login(sender_email, sender_password)  # 登录到 SMTP 服务器
            server.sendmail(sender_email, recipient_email, message.as_string())  # 发送邮件
        print(f"Email successfully sent to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
    
@user_router.put("/{user_id}")
def update_user(user_id: int, user_data: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == str(user_id)).first()  # 将 UUID 转为字符串匹配数据库
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.username = user_data.username or user.username
    user.email = user_data.email or user.email
    user.role = user_data.role or user.role
    user.updated_at = datetime.now()

    db.commit()
    db.refresh(user)

    return {"message": "User updated successfully", "user": user}

@user_router.delete("/{user_id}")
def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == str(user_id)).first()  # 将 UUID 转为字符串匹配数据库
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
