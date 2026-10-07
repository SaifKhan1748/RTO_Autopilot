from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, ARRAY, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Office(Base):
    __tablename__ = "offices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    display_name = Column(String(100), nullable=True)  # Custom display name for branding
    address = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    staff = relationship("Staff", back_populates="office")
    cases = relationship("Case", back_populates="office")
    customers = relationship("Customer", back_populates="office")
    checklist_configs = relationship("ChecklistConfig", back_populates="office")

class Staff(Base):
    """
    Staff model - represents employees who work at an office and can log in.
    Each staff member belongs to exactly one office.
    """
    __tablename__ = "staff"
    
    id = Column(Integer, primary_key=True, index=True)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # Hashed password
    full_name = Column(String(100), nullable=False)
    role = Column(String(50), default="staff")  # Role: admin, staff, etc.
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    failed_login_attempts = Column(Integer, default=0)  # Track failed login attempts
    locked_until = Column(DateTime(timezone=True), nullable=True)  # Account lockout expiration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    office = relationship("Office", back_populates="staff")

class Customer(Base):
    """
    Customer model - represents people who visit the RTO office.
    Each customer belongs to exactly one office.
    """
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    address = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    office = relationship("Office", back_populates="customers")
    cases = relationship("Case", back_populates="customer", cascade="all, delete-orphan")

class Case(Base):
    """
    Case model - represents a vehicle registration case/service request.
    Each case belongs to one customer and one office.
    """
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, index=True)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    service_type = Column(String(50), nullable=False)  # e.g., "New Registration", "Transfer", "Renewal"
    status = Column(String(20), default="pending")  # pending, in_progress, completed, rejected
    vehicle_number = Column(String(20))  # Vehicle registration number
    notes = Column(Text)  # Additional notes about the case
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    office = relationship("Office", back_populates="cases")
    customer = relationship("Customer", back_populates="cases")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="case")
    reminders = relationship("PendingReminder", back_populates="case", cascade="all, delete-orphan")

class Document(Base):
    """
    Document model - represents documents uploaded for a case.
    Each document belongs to exactly one case.
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)  # For office-specific queries
    document_type = Column(String(50), nullable=False)  # e.g., "ID Proof", "Address Proof", "Vehicle RC"
    file_name = Column(String(255))  # Name of the uploaded file
    r2_object_key = Column(String(500))  # R2 object key (replaces local file_path)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="documents")

class Event(Base):
    """
    Event model - an append-only log of what happened to a case.
    This creates a complete audit trail for each case.
    Each event belongs to exactly one case, or to the office in administrative events (e.g. customer deletion).
    """
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)  # For office-specific queries
    event_type = Column(String(50), nullable=False)  # e.g., "created", "status_changed", "document_uploaded"
    description = Column(Text, nullable=False)  # Human-readable description of what happened
    created_by = Column(String(100))  # Email of staff member who triggered this event
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="events")

class PendingReminder(Base):
    """
    PendingReminder model - represents automatic reminders that need staff approval.
    This is used for the automatic reminder system that checks for cases where
    documents were requested more than 2 days ago but still haven't been uploaded.
    """
    __tablename__ = "pending_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)  # For office-specific queries
    message = Column(Text, nullable=False)  # The drafted reminder message
    status = Column(String(20), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))  # When the reminder was approved/rejected
    
    # Relationships
    case = relationship("Case", back_populates="reminders")

class PolicyChunk(Base):
    """
    PolicyChunk model - represents chunks of policy documents with embeddings for RAG.
    Used for retrieving relevant policy information based on user questions.
    """
    __tablename__ = "policy_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(50), nullable=False, index=True)  # e.g., "Karnataka", "Maharashtra"
    service_type = Column(String(50), nullable=False, index=True)  # e.g., "License Renewal", "New Registration"
    source_name = Column(String(255), nullable=False)  # Original document filename
    chunk_text = Column(Text, nullable=False)  # The actual text chunk
    embedding = Column(ARRAY(Float), nullable=False)  # Embedding vector stored as array (384 dimensions)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChecklistConfig(Base):
    """
    ChecklistConfig model - represents customizable checklist configurations for each office.
    Allows offices to define which documents are required for each service type.
    """
    __tablename__ = "checklist_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)
    service_type = Column(String(50), nullable=False)  # e.g., "New Registration", "Transfer", "Renewal"
    document_type = Column(String(50), nullable=False)  # e.g., "ID Proof", "Address Proof", "Vehicle RC"
    is_required = Column(Integer, default=1)  # 1 = required, 0 = optional
    display_order = Column(Integer, default=0)  # Order in which to display the checklist
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    office = relationship("Office", back_populates="checklist_configs")

class PasswordReset(Base):
    """
    PasswordReset model - represents password reset tokens.
    Used for the forgot password flow.
    """
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)  # Reset token
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Token expiration time
    used = Column(Integer, default=0)  # 0 = not used, 1 = used
    created_at = Column(DateTime(timezone=True), server_default=func.now())
