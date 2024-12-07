from fastapi import APIRouter, Depends, HTTPException,Form
from sqlalchemy.orm import Session
from app.models.user import User
from app.database import get_db
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import enum
import smtplib


user_router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
class UserRole(enum.Enum):
    CUSTOMER = "customer"
    MERCHANT = "merchant"

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str
    store_id: Optional[str] = None

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

@user_router.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        # 用户不存在
        raise HTTPException(status_code=404, detail="User not found")
    elif (password is None) or (user.password != password):
        # 密码不匹配
        raise HTTPException(status_code=401, detail="Incorrect password")
    else:
        # 登录成功
        return {"message": "Login successful", "user_id": user.id, "email": user.email}

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