from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)

class WasteRecord(Base):
    __tablename__ = 'waste_records'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    date_collected = Column(DateTime, default=datetime.now)
    data = Column(JSON)  # Store waste data as JSON

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
