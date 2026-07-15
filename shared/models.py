import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime,
    ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from .database import Base


class GoalEnum(str, enum.Enum):
    own_objects = "own_objects"
    earn_money = "earn_money"
    exploring_ai = "exploring_ai"


class ConsentTypeEnum(str, enum.Enum):
    offer = "offer"
    personal_data = "personal_data"


class ObjectStatusEnum(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    assigned = "assigned"
    rejected = "rejected"


class MailingStatusEnum(str, enum.Enum):
    pending = "pending"
    sending = "sending"
    sent = "sent"
    cancelled = "cancelled"
    error = "error"


class MailingCategoryEnum(str, enum.Enum):
    all = "all"
    own_objects = "own_objects"
    earn_money = "earn_money"
    exploring_ai = "exploring_ai"


class MailingLogStatusEnum(str, enum.Enum):
    sent = "sent"
    failed = "failed"


class LegalDocTypeEnum(str, enum.Enum):
    offer = "offer"
    privacy_policy = "privacy_policy"
    personal_data_policy = "personal_data_policy"
    free_lessons = "free_lessons"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    goal = Column(Enum(GoalEnum), nullable=True)
    consent_offer = Column(Boolean, default=False)
    consent_personal_data = Column(Boolean, default=False)
    funnel_stage = Column(String(50), default="start")
    support_thread_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consent_logs = relationship("ConsentLog", back_populates="user")
    questions = relationship("Question", back_populates="user")
    objects = relationship("Object", back_populates="user", foreign_keys="Object.user_id")
    assigned_objects = relationship("Object", back_populates="assigned_user", foreign_keys="Object.assigned_to")
    mailing_logs = relationship("MailingLog", back_populates="user")
    events = relationship("AnalyticsEvent", back_populates="user")


class ConsentLog(Base):
    __tablename__ = "consent_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    consent_type = Column(Enum(ConsentTypeEnum), nullable=False)
    accepted = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="consent_logs")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message_text = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="questions")


class Object(Base):
    __tablename__ = "objects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    object_name = Column(String(500), nullable=False)
    address = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    photo_links = Column(Text, nullable=True)
    video_links = Column(Text, nullable=True)
    budget = Column(String(255), nullable=True)
    status = Column(Enum(ObjectStatusEnum), default=ObjectStatusEnum.pending)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="objects", foreign_keys=[user_id])
    assigned_user = relationship("User", back_populates="assigned_objects", foreign_keys=[assigned_to])


class Mailing(Base):
    __tablename__ = "mailings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_text = Column(Text, nullable=False)
    target_category = Column(Enum(MailingCategoryEnum), nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    status = Column(Enum(MailingStatusEnum), default=MailingStatusEnum.pending)
    created_at = Column(DateTime, default=datetime.utcnow)

    logs = relationship("MailingLog", back_populates="mailing")


class MailingLog(Base):
    __tablename__ = "mailing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mailing_id = Column(Integer, ForeignKey("mailings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(MailingLogStatusEnum), nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)

    mailing = relationship("Mailing", back_populates="logs")
    user = relationship("User", back_populates="mailing_logs")


class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_type = Column(Enum(LegalDocTypeEnum), nullable=False)
    file_path = Column(Text, nullable=False)
    file_name = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="events")
