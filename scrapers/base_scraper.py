import hashlib
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobResult(BaseModel):
    title: str
    company: str
    location: str | None = None
    is_remote: bool = False
    salary_min: float | None = None
    salary_max: float | None = None
    salary_raw: str | None = None
    description: str | None = None
    job_url: str
    apply_url: str | None = None
    source: str
    ats_platform: str | None = None
    experience_min: int | None = None
    experience_max: int | None = None
    tech_stack: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    date_posted: datetime | None = None
    company_tier: str | None = None
    company_domain: str | None = None
    tags: list[str] = Field(default_factory=list)

    def generate_id(self) -> str:
        s = f"{self.company}|{self.title}|{self.job_url}".lower()
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def to_db_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        job_id = self.generate_id()
        d['id'] = job_id
        d['job_hash'] = job_id
        return d


class BaseScraper(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def scrape(self, query: str, location: str, **kwargs) -> list[JobResult]:
        pass

    def _normalize_salary_to_lpa(self, salary_str: str) -> tuple[float | None, float | None]:
        if not salary_str:
            return None, None
        
        s = salary_str.lower().replace(',', '')
        
        numbers = [float(n) for n in re.findall(r'\d+\.?\d*', s)]
        if not numbers:
            return None, None
        
        min_val = numbers[0]
        max_val = numbers[1] if len(numbers) > 1 else min_val
        
        if any(term in s for term in ['lpa', 'lac', 'lakh', 'lacs', 'lakhs']):
            return min_val, max_val
        elif '$' in s:
            if 'k' in s:
                # $80k -> 80 * 83 / 100 = 66.4 LPA
                return round(min_val * 83 / 100, 2), round(max_val * 83 / 100, 2)
            elif min_val >= 1000:
                # $100000 -> 100000 * 83 / 100000 = 83.0 LPA
                return round((min_val * 83) / 100000, 2), round((max_val * 83) / 100000, 2)
            else:
                # $100 -> likely hourly or unknown
                return None, None
        elif any(term in s for term in ['month', 'pm', '/m']):
            return round((min_val * 12) / 100000, 2), round((max_val * 12) / 100000, 2)
        elif min_val >= 100000:
            # Stated in raw INR per annum (e.g., 1200000)
            return round(min_val / 100000, 2), round(max_val / 100000, 2)
            
        return None, None

    def _extract_tech_stack(self, description: str) -> list[str]:
        if not description:
            return []
        
        keywords = ['python', 'java', 'c++', 'go', 'rust', 'javascript', 'typescript', 'react', 'angular', 'vue', 
                    'node.js', 'django', 'flask', 'fastapi', 'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'sql', 'nosql', 'postgres', 'mongodb']
        
        desc_lower = description.lower()
        found = []
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', desc_lower):
                found.append(kw)
        return list(set(found))
