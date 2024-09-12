from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Define the base for the models
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)

# WasteRecord model
class WasteRecord(Base):
    __tablename__ = 'waste_records'
    id = Column(Integer, primary_key=True)
    date_collected = Column(Date, nullable=False)
    landfill_waste = Column(Float)
    food_waste = Column(Float)
    aluminum = Column(Float)
    cardboard = Column(Float)
    glass = Column(Float)
    metal_cans = Column(Float)
    metal_scrap = Column(Float)
    paper_books = Column(Float)
    paper_mixed = Column(Float)
    paper_newspaper = Column(Float)
    paper_white = Column(Float)
    plastic_pet = Column(Float)
    plastic_hdpe_colored = Column(Float)
    plastic_hdpe_natural = Column(Float)
    user_id = Column(Integer, ForeignKey('users.id'))

    # Relationship to the User model
    user = relationship("User", back_populates="waste_records")

# Category model
class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

# Define the relationship between User and WasteRecord
User.waste_records = relationship("WasteRecord", order_by=WasteRecord.id, back_populates="user")

# Create the database engine
engine = create_engine('sqlite:///recycle_center.db')

# Create all tables
Base.metadata.create_all(engine)

# Create the session for interacting with the database
Session = sessionmaker(bind=engine)
session = Session()
