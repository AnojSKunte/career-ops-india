import os
import json
import hashlib
import logging
import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import create_engine, select, or_, and_, func, update
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, Job, Application, ScrapeRun, Contact

logger = logging.getLogger(__name__)

class JobStore:
    def __init__(self, db_path: str = "data/career_ops.db"):
        db_path_obj = Path(db_path)
        if not db_path_obj.parent.exists():
            db_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def _generate_job_id(self, company: str, title: str, url: str) -> str:
        s = f"{company or ''}|{title or ''}|{url or ''}".lower()
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def upsert_job(self, job_dict: dict) -> Job:
        job_url = job_dict.get('job_url')
        company = job_dict.get('company', '')
        title = job_dict.get('title', '')
        
        job_id = job_dict.get('id') or self._generate_job_id(company, title, job_url or '')
        
        with self.session_scope() as session:
            job = session.execute(
                select(Job).filter(Job.id == job_id)
            ).scalar_one_or_none()
            
            if not job and job_url:
                job = session.execute(
                    select(Job).filter(Job.job_url == job_url)
                ).scalar_one_or_none()

            if job:
                # Update without overwriting existing data with None
                for key, value in job_dict.items():
                    if hasattr(job, key) and key != 'id':
                        if value is not None or getattr(job, key) is None:
                            setattr(job, key, value)
                job.last_seen = datetime.datetime.now()
            else:
                # Insert
                job_data = {k: v for k, v in job_dict.items() if hasattr(Job, k)}
                job_data['id'] = job_id
                job = Job(**job_data)
                session.add(job)
            
            session.flush()
            session.refresh(job)
            return job

    def upsert_jobs(self, jobs: List[dict]) -> Tuple[int, int]:
        new_count = 0
        updated_count = 0
        
        with self.session_scope() as session:
            for job_dict in jobs:
                job_url = job_dict.get('job_url')
                company = job_dict.get('company', '')
                title = job_dict.get('title', '')
                job_id = job_dict.get('id') or self._generate_job_id(company, title, job_url or '')
                
                job = session.execute(
                    select(Job).filter(Job.id == job_id)
                ).scalar_one_or_none()
                
                if not job and job_url:
                    job = session.execute(
                        select(Job).filter(Job.job_url == job_url)
                    ).scalar_one_or_none()

                if job:
                    for key, value in job_dict.items():
                        if hasattr(job, key) and key != 'id':
                            if value is not None or getattr(job, key) is None:
                                setattr(job, key, value)
                    job.last_seen = datetime.datetime.now()
                    updated_count += 1
                else:
                    job_data = {k: v for k, v in job_dict.items() if hasattr(Job, k)}
                    job_data['id'] = job_id
                    job = Job(**job_data)
                    session.add(job)
                    new_count += 1
                    
        return new_count, updated_count

    def get_job(self, job_id: str) -> Optional[Job]:
        with self.session_scope() as session:
            return session.execute(select(Job).filter(Job.id == job_id)).scalar_one_or_none()

    def get_jobs(self, filters: dict) -> List[Job]:
        with self.session_scope() as session:
            query = select(Job)
            
            if 'source' in filters:
                query = query.filter(Job.source == filters['source'])
            if 'company' in filters:
                query = query.filter(Job.company.ilike(f"%{filters['company']}%"))
            if 'grade' in filters:
                query = query.filter(Job.grade == filters['grade'])
            if 'is_active' in filters:
                query = query.filter(Job.is_active == filters['is_active'])
            if 'min_score' in filters:
                query = query.filter(Job.fit_score >= filters['min_score'])
                
            return list(session.execute(query).scalars().all())

    def search_jobs(self, query_str: str) -> List[Job]:
        with self.session_scope() as session:
            query = select(Job).filter(
                or_(
                    Job.title.ilike(f"%{query_str}%"),
                    Job.description.ilike(f"%{query_str}%")
                )
            )
            return list(session.execute(query).scalars().all())

    def get_active_jobs(self, min_grade: Optional[str] = None) -> List[Job]:
        with self.session_scope() as session:
            query = select(Job).filter(Job.is_active == True)
            if min_grade:
                grade_order = ['A', 'B', 'C', 'D', 'F']
                if min_grade.upper() in grade_order:
                    idx = grade_order.index(min_grade.upper())
                    allowed_grades = grade_order[:idx + 1]
                    query = query.filter(Job.grade.in_(allowed_grades))
            return list(session.execute(query).scalars().all())

    def mark_inactive(self, job_url: str):
        with self.session_scope() as session:
            session.execute(
                update(Job).where(Job.job_url == job_url).values(is_active=False)
            )

    def update_score(self, job_id: str, score: float, grade: str, details: dict):
        with self.session_scope() as session:
            session.execute(
                update(Job).where(Job.id == job_id).values(
                    fit_score=score,
                    grade=grade,
                    scoring_details=details
                )
            )

    def get_stats(self) -> Dict[str, Any]:
        stats = {}
        with self.session_scope() as session:
            # Source counts
            sources = session.execute(select(Job.source, func.count(Job.id)).group_by(Job.source)).all()
            stats['by_source'] = {s: c for s, c in sources if s}
            
            # Grade counts
            grades = session.execute(select(Job.grade, func.count(Job.id)).group_by(Job.grade)).all()
            stats['by_grade'] = {g: c for g, c in grades if g}
            
            # Active/Inactive
            active = session.execute(select(func.count(Job.id)).filter(Job.is_active == True)).scalar() or 0
            inactive = session.execute(select(func.count(Job.id)).filter(Job.is_active == False)).scalar() or 0
            stats['active_status'] = {'active': active, 'inactive': inactive}
            
        return stats

    def log_scrape_run(self, source: str, jobs_found: int, jobs_new: int, jobs_updated: int, status: str, error: str = None):
        with self.session_scope() as session:
            run = ScrapeRun(
                source=source,
                started_at=datetime.datetime.now(),
                completed_at=datetime.datetime.now(),
                jobs_found=jobs_found,
                jobs_new=jobs_new,
                jobs_updated=jobs_updated,
                status=status,
                error_message=error
            )
            session.add(run)

    def upsert_contact(self, contact_dict: dict) -> Contact:
        with self.session_scope() as session:
            email = contact_dict.get('email')
            contact = None
            if email:
                contact = session.execute(select(Contact).filter(Contact.email == email)).scalar_one_or_none()
            
            if contact:
                for k, v in contact_dict.items():
                    if hasattr(contact, k) and k != 'id':
                        setattr(contact, k, v)
            else:
                contact_data = {k: v for k, v in contact_dict.items() if hasattr(Contact, k)}
                contact = Contact(**contact_data)
                session.add(contact)
                
            session.flush()
            session.refresh(contact)
            return contact

    def get_contacts(self, company: str) -> List[Contact]:
        with self.session_scope() as session:
            return list(session.execute(select(Contact).filter(Contact.company.ilike(f"%{company}%"))).scalars().all())

    def create_application(self, job_id: str, status: str = 'to_apply') -> Application:
        with self.session_scope() as session:
            app = Application(
                job_id=job_id,
                status=status,
                date_found=datetime.datetime.now(),
                date_updated=datetime.datetime.now()
            )
            session.add(app)
            session.flush()
            session.refresh(app)
            return app

    def update_application(self, app_id: int, **kwargs):
        with self.session_scope() as session:
            app = session.execute(select(Application).filter(Application.id == app_id)).scalar_one_or_none()
            if app:
                for k, v in kwargs.items():
                    if hasattr(app, k):
                        setattr(app, k, v)
                app.date_updated = datetime.datetime.now()

    def get_applications(self, status: Optional[str] = None) -> List[Application]:
        with self.session_scope() as session:
            query = select(Application)
            if status:
                query = query.filter(Application.status == status)
            return list(session.execute(query).scalars().all())

    def get_pipeline_stats(self) -> Dict[str, Any]:
        with self.session_scope() as session:
            status_counts = session.execute(select(Application.status, func.count(Application.id)).group_by(Application.status)).all()
            stats = {'by_status': {s: c for s, c in status_counts if s}}
            
            total = sum(stats['by_status'].values())
            stats['total_applications'] = total
            
            # Simple conversion rate (interview vs total applied)
            interview_stages = ['hr_screen', 'technical', 'final_round', 'offer', 'accepted']
            interview_count = sum(stats['by_status'].get(s, 0) for s in interview_stages)
            
            stats['interview_rate'] = (interview_count / total * 100) if total > 0 else 0
            return stats

    def export_pipeline_json(self) -> List[Dict[str, Any]]:
        with self.session_scope() as session:
            apps = session.execute(select(Application)).scalars().all()
            return [
                {
                    "id": app.id,
                    "job_id": app.job_id,
                    "status": app.status,
                    "date_found": app.date_found.isoformat() if app.date_found else None,
                    "date_applied": app.date_applied.isoformat() if app.date_applied else None,
                    "notes": app.notes,
                    "contact_name": app.contact_name,
                    "contact_email": app.contact_email
                }
                for app in apps
            ]

    def import_pipeline_json(self, path: str):
        if not os.path.exists(path):
            return
            
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        with self.session_scope() as session:
            for item in data:
                job_id = item.get("job_id")
                if not job_id:
                    continue
                    
                app = session.execute(select(Application).filter(Application.job_id == job_id)).scalar_one_or_none()
                if not app:
                    app = Application(job_id=job_id)
                    session.add(app)
                
                app.status = item.get("status", app.status)
                app.notes = item.get("notes", app.notes)
                if item.get("date_applied"):
                    app.date_applied = datetime.datetime.fromisoformat(item["date_applied"])
