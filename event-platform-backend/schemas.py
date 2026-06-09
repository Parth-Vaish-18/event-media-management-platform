from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import List, Optional
from datetime import datetime
from models import UserRole
import json


# ---------------------------------------------------------------------------
# USER SCHEMAS
# ---------------------------------------------------------------------------
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    password: str
    admin_secret: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# EVENT SCHEMAS
# ---------------------------------------------------------------------------
class EventBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    date: datetime


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# COMMENT SCHEMAS
# ---------------------------------------------------------------------------
class CommentCreate(BaseModel):
    text: str


class CommentResponse(BaseModel):
    id: int
    user_id: int
    # FIX: 'user_name' was in original schema but the ORM field is user.name.
    # We return 'user' (str) directly from the endpoint dict — no ORM mapping needed.
    text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# MEDIA SCHEMAS
# ---------------------------------------------------------------------------
class MediaResponse(BaseModel):
    id: int
    s3_url: str
    event_id: int
    uploader_id: int
    is_public: bool
    # FIX: ai_tags is stored as a JSON string in SQLite. This validator parses it.
    ai_tags: List[str]
    person_detected: Optional[str] = None
    is_liked: bool = False
    is_favorited: bool = False
    like_count: int = 0
    views_count: int = 0
    is_highlight: bool = False
    downloads: int = 0
    shares: int = 0
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("ai_tags", mode="before")
    @classmethod
    def parse_ai_tags(cls, v):
        """Parse JSON string to list if needed."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        if v is None:
            return []
        return v
