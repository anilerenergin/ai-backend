from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    jobs = relationship("Job", back_populates="owner")  # lowercase 'r'

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text)
    image_url = Column(String)
    result_url = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    application = Column(String, nullable=True)  # pending, processing, completed, failed
    fal_request_id = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="jobs")  # lowercase 'r'
    strength = Column(Float, default=0.7)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())