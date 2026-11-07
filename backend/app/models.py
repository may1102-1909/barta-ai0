import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    discount_price = Column(Float, nullable=True)
    url = Column(String(500), nullable=False)
    details = Column(JSON, default=dict) # sizes, colors, fabric, return policy
    created_at = Column(DateTime(timezone=True), default=utc_now)

    campaigns = relationship("Campaign", back_populates="product")
    orders = relationship("Order", back_populates="product")

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    goal = Column(Text, nullable=False)
    max_concurrent = Column(Integer, default=1)
    window_start = Column(String(10), default="09:00") # IST "HH:MM"
    window_end = Column(String(10), default="20:00")   # IST "HH:MM"
    retry_limit = Column(Integer, default=2)
    status = Column(String(50), default="draft") # draft, active, paused, completed
    product_url = Column(Text, nullable=True)
    script = Column(Text, nullable=True)
    language = Column(String(50), default="hinglish")
    created_at = Column(DateTime(timezone=True), default=utc_now)

    product = relationship("Product", back_populates="campaigns")
    contacts = relationship("Contact", back_populates="campaign", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="campaign")

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False) # E.164 format (+91...)
    email = Column(String(255), nullable=True)
    language = Column(String(50), default="hinglish") # hinglish, hindi, english
    status = Column(String(50), default="new") # new, dialing, done, dnc
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    campaign = relationship("Campaign", back_populates="contacts")
    calls = relationship("Call", back_populates="contact", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="contact")
    callbacks = relationship("Callback", back_populates="contact")
    messages = relationship("Message", back_populates="contact")

class Call(Base):
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    contact_id = Column(String(36), ForeignKey("contacts.id"), nullable=False)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False)
    twilio_sid = Column(String(100), nullable=True)
    status = Column(String(50), default="queued") # queued, in-progress, completed, failed, busy, no-answer
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_sec = Column(Integer, default=0)
    outcome = Column(String(50), nullable=True) # order_confirmed, interested, callback_requested, not_interested, no_answer, wrong_number, do_not_call
    summary = Column(Text, nullable=True)
    transcript = Column(JSON, default=list) # [{"speaker": "agent"|"user", "text": "...", "timestamp": "..."}]
    language_detected = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    contact = relationship("Contact", back_populates="calls")
    campaign = relationship("Campaign", back_populates="calls")
    orders = relationship("Order", back_populates="call")
    callbacks = relationship("Callback", back_populates="source_call")

class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    contact_id = Column(String(36), ForeignKey("contacts.id"), nullable=False)
    call_id = Column(String(36), ForeignKey("calls.id"), nullable=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(String(50), default="awaiting_details") # awaiting_details, details_received, paid, cod, cancelled
    form_token = Column(String(100), unique=True, nullable=False)
    form_expires_at = Column(DateTime(timezone=True), nullable=False)
    customer_name = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)
    payment_method = Column(String(50), nullable=True) # cod, razorpay
    created_at = Column(DateTime(timezone=True), default=utc_now)

    contact = relationship("Contact", back_populates="orders")
    call = relationship("Call", back_populates="orders")
    product = relationship("Product", back_populates="orders")

class Callback(Base):
    __tablename__ = "callbacks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    contact_id = Column(String(36), ForeignKey("contacts.id"), nullable=False)
    source_call_id = Column(String(36), ForeignKey("calls.id"), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=False) # Stored in UTC
    reason = Column(Text, nullable=True)
    status = Column(String(50), default="pending") # pending, in_progress, done, cancelled
    created_at = Column(DateTime(timezone=True), default=utc_now)

    contact = relationship("Contact", back_populates="callbacks")
    source_call = relationship("Call", back_populates="callbacks")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    contact_id = Column(String(36), ForeignKey("contacts.id"), nullable=True)
    channel = Column(String(50), nullable=False) # email, whatsapp
    direction = Column(String(50), nullable=False) # inbound, outbound
    body = Column(Text, nullable=False)
    status = Column(String(50), default="sent") # sent, received, failed
    created_at = Column(DateTime(timezone=True), default=utc_now)

    contact = relationship("Contact", back_populates="messages")

