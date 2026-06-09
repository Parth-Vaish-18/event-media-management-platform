from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base


class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    PHOTOGRAPHER = "Photographer"
    MEMBER = "Club Member"
    VIEWER = "Viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)

    # AI Feature: Facial Recognition — stored as JSON string
    face_encoding = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    media_uploaded = relationship("Media", back_populates="uploader")
    likes = relationship("Like", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    favorites = relationship("Favorite", back_populates="user")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, index=True, nullable=True)
    date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    media = relationship("Media", back_populates="event", cascade="all, delete-orphan")


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    s3_url = Column(String, nullable=False)
    is_public = Column(Boolean, default=True)

    # AI Features
    ai_tags = Column(Text, nullable=True)          # JSON string, e.g. '["mountains", "sky"]'
    person_detected = Column(String, nullable=True) # Comma-separated matched user names

    # Engagement counters
    downloads = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    views_count = Column(Integer, default=0)

    # Bonus: Story/Highlight feature
    is_highlight = Column(Boolean, default=False)

    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="media")
    uploader = relationship("User", back_populates="media_uploaded")
    likes = relationship("Like", back_populates="media", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="media", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="media", cascade="all, delete-orphan")


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    media_id = Column(Integer, ForeignKey("media.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="likes")
    media = relationship("Media", back_populates="likes")


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    media_id = Column(Integer, ForeignKey("media.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    media = relationship("Media", back_populates="favorites")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    media_id = Column(Integer, ForeignKey("media.id"), nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="comments")
    media = relationship("Media", back_populates="comments")
