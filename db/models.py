import datetime
from typing import Any, List, Optional
from sqlalchemy import (
    String,
    Float,
    Boolean,
    Text,
    Integer,
    DateTime,
    JSON,
    ForeignKey,
    func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    company: Mapped[str] = mapped_column(String, nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    salary_min: Mapped[Optional[float]] = mapped_column(Float)
    salary_max: Mapped[Optional[float]] = mapped_column(Float)
    salary_raw: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text)
    description_snippet: Mapped[Optional[str]] = mapped_column(String(500))
    job_url: Mapped[Optional[str]] = mapped_column(String, unique=True)
    apply_url: Mapped[Optional[str]] = mapped_column(String)
    source: Mapped[Optional[str]] = mapped_column(String, index=True)
    ats_platform: Mapped[Optional[str]] = mapped_column(String)
    experience_min: Mapped[Optional[int]] = mapped_column(Integer)
    experience_max: Mapped[Optional[int]] = mapped_column(Integer)
    tech_stack: Mapped[Optional[List[str]]] = mapped_column(JSON)
    requirements: Mapped[Optional[List[str]]] = mapped_column(JSON)
    company_tier: Mapped[Optional[str]] = mapped_column(String)
    company_domain: Mapped[Optional[str]] = mapped_column(String)
    date_posted: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    first_seen: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_seen: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    fit_score: Mapped[Optional[float]] = mapped_column(Float)
    grade: Mapped[Optional[str]] = mapped_column(String(10))
    scoring_details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    source_urls: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="job")

class Application(Base):
    __tablename__ = "applications"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[Optional[str]] = mapped_column(String)
    date_found: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    date_applied: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    date_updated: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    resume_version: Mapped[Optional[str]] = mapped_column(String)
    contact_name: Mapped[Optional[str]] = mapped_column(String)
    contact_email: Mapped[Optional[str]] = mapped_column(String)
    follow_up_due: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String)
    
    job: Mapped["Job"] = relationship("Job", back_populates="applications")

class ScrapeRun(Base):
    __tablename__ = "scrape_runs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[Optional[str]] = mapped_column(String)
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    jobs_found: Mapped[Optional[int]] = mapped_column(Integer)
    jobs_new: Mapped[Optional[int]] = mapped_column(Integer)
    jobs_updated: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[Optional[str]] = mapped_column(String)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

class Contact(Base):
    __tablename__ = "contacts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company: Mapped[Optional[str]] = mapped_column(String)
    name: Mapped[Optional[str]] = mapped_column(String)
    title: Mapped[Optional[str]] = mapped_column(String)
    email: Mapped[Optional[str]] = mapped_column(String)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String)
    relevance: Mapped[Optional[str]] = mapped_column(String)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    discovered_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    source: Mapped[Optional[str]] = mapped_column(String)
