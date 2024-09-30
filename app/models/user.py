from sqlalchemy import Column, String, Float, Integer, Enum as SQLEnum, DateTime, JSON
from datetime import datetime
import uuid
import enum

from app.database import Base
class UserRole(enum.Enum):
    CUSTOMER = "customer"
    MERCHANT = "merchant"

class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(String(1000), default="")
    price = Column(Float, default=0.0)
    stock = Column(Integer, default=0)
    images = Column(JSON, default=list)
    extra = Column(JSON, default=dict)
    store_id = Column(String(36), default=None)

class Store(Base):
    __tablename__ = "stores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), default="")
    address = Column(String(500), default="")
    description = Column(String(1000), default="")
    images = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    extra = Column(JSON, default=dict)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), default="")
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.CUSTOMER)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    extra = Column(JSON, default=dict)
    store_id = Column(String(36), default=None)