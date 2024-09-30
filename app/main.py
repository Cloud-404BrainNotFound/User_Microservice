from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app import models
from app.database import engine, get_db
from app.models import user
from fastapi.middleware.cors import CORSMiddleware
from app.routers.user_service import user_router  # 导入用户相关的 router

# 创建数据库表
user.Base.metadata.create_all(bind=engine)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# 这是一个router的示例
app.include_router(user_router, prefix="/users", tags=["users"])


@app.get("/")
def read_root():
    return {"Hello": "World"}