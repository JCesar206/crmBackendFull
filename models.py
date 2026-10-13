from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Client(Base):
		__tablename__ = "clients"

		id = Column(Integer, primary_key=True, index=True, autoincrement=True)
		name = Column(String(100), nullable=False)
		email = Column(String(100), nullable=False)
		phone = Column(String(50), nullable=True)
		owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
		created_at = Column(DateTime, default=datetime.utcnow)