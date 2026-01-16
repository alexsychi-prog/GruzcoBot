from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    role = Column(String(20), default="manager", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tasks = relationship("Task", back_populates="manager", lazy="dynamic")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, role={self.role})>"


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    deadline = Column(DateTime, nullable=False)
    status = Column(String(20), default="active", nullable=False)
    completed_at = Column(DateTime, nullable=True)
    not_completed_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    manager = relationship("User", back_populates="tasks")
    
    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status}, deadline={self.deadline})>"


class GroupAnalytics(Base):
    __tablename__ = "group_analytics"
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, unique=True, nullable=False, index=True)
    group_title = Column(String(255), nullable=True)
    total_members = Column(Integer, default=0)
    left_members = Column(Integer, default=0)
    kicked_members = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<GroupAnalytics(group_id={self.group_id}, total={self.total_members})>"


class GroupMember(Base):
    __tablename__ = "group_members"
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("group_analytics.id"), nullable=False)
    telegram_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    status = Column(String(20), default="active", nullable=False)
    left_at = Column(DateTime, nullable=True)
    
    group = relationship("GroupAnalytics", back_populates="members")
    
    def __repr__(self):
        return f"<GroupMember(telegram_id={self.telegram_id}, status={self.status})>"


class CleanupLog(Base):
    __tablename__ = "cleanup_logs"
    
    id = Column(Integer, primary_key=True)
    last_cleanup_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    tasks_deleted = Column(Integer, default=0)
    cleanup_type = Column(String(20), default="manual", nullable=False)  # "manual" or "auto"
    
    def __repr__(self):
        return f"<CleanupLog(last_cleanup={self.last_cleanup_date}, deleted={self.tasks_deleted})>"

