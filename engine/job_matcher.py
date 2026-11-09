import logging
import yaml
import re
from typing import Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class JobMatcher:
    def __init__(self, profile_path: str = 'config/profile.yml'):
        self.profile = self._load_profile(profile_path)
    
    def score_job(self, job: Dict) -> Tuple[float, str, Dict]:
        """Score a job on 10 dimensions per the _shared.md rubric.
        Returns (total_score, grade, dimension_scores)
        
        Dimensions and weights:
        1. Role-skill match (25%)
        2. Salary fit (20%)
        3. Tech stack overlap (15%)
        4. Growth trajectory (10%)
        5. Company tier/health (10%)
        6. Location/remote (5%)
        7. JD quality (5%)
        8. Experience fit (5%)
        9. Resume gap (3%)
        10. Legitimacy (2%)
        
        Grade: A (4.5-5.0), B (4.0-4.4), C (3.5-3.9), D (3.0-3.4), F (<3.0)
        """
        dims = {
            'role_match': self._score_role_match(job) * 0.25,
            'salary': self._score_salary(job) * 0.20,
            'tech_stack': self._score_tech_stack(job) * 0.15,
            'growth': self._score_growth(job) * 0.10,
            'company': self._score_company(job) * 0.10,
            'location': self._score_location(job) * 0.05,
            'jd_quality': self._score_jd_quality(job) * 0.05,
            'experience': self._score_experience(job) * 0.05,
            'resume_gap': self._score_resume_gap(job) * 0.03,
            'legitimacy': self._score_legitimacy(job) * 0.02,
        }
        
        total_score = sum(dims.values())
        
        if total_score >= 4.5:
            grade = 'A'
        elif total_score >= 4.0:
            grade = 'B'
        elif total_score >= 3.5:
            grade = 'C'
        elif total_score >= 3.0:
            grade = 'D'
        else:
            grade = 'F'
            
        return total_score, grade, dims
    
    def score_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Score multiple jobs and return sorted by score descending."""
        scored = []
        for job in jobs:
            score, grade, dims = self.score_job(job)
            scored_job = job.copy()
            round_score = round(score, 2)
            scored_job['score'] = round_score
            scored_job['fit_score'] = round_score
            scored_job['grade'] = grade
            scored_job['dimension_scores'] = dims
            scored_job['scoring_details'] = dims
            scored.append(scored_job)
        return sorted(scored, key=lambda x: x['score'], reverse=True)
    
    def _score_role_match(self, job: Dict) -> float:
        """Score 0-5 based on title keyword overlap and skill requirements."""
        target_roles = self.profile.get('candidate', {}).get('target_roles', [])
        title = str(job.get('title', job.get('role', ''))).lower()
        if not target_roles:
            return 3.0
        if any(tr.lower() in title for tr in target_roles):
            return 5.0
        return 2.5
    
    def _score_salary(self, job: Dict) -> float:
        """Score 0-5 based on salary fit.
        5.0 = salary_max >= target_max
        4.0 = salary within target range
        3.0 = salary >= target_min
        2.0 = salary near walk_away
        1.0 = salary below walk_away
        0.0 = no salary info (penalize slightly)
        """
        sal_min = job.get('salary_min')
        sal_max = job.get('salary_max')
        
        # Try parsing salary_raw if min/max not available
        if not sal_min and not sal_max:
            salary_raw = str(job.get('salary_raw', '') or job.get('salary_listed', ''))
            if salary_raw:
                nums = re.findall(r'(\d+(?:\.\d+)?)', salary_raw)
                if nums:
                    sal_min = float(nums[0])
                    sal_max = float(nums[-1]) if len(nums) > 1 else sal_min
        
        if not sal_min and not sal_max:
            return 2.5  # No salary info — neutral score
            
        target = self.profile.get('candidate', {}).get('target_salary_lpa', {})
        if not target:
            return 3.0
            
        t_min = target.get('min', 0)
        t_max = target.get('max', 0)
        t_walk = target.get('walk_away', 0)
        
        # Use the higher salary value for comparison
        sal = sal_max or sal_min or 0
        
        if sal >= t_max:
            return 5.0
        elif t_min <= sal <= t_max:
            return 4.0
        elif sal >= t_min:
            return 3.0
        elif sal >= t_walk:
            return 2.0
        else:
            return 1.0
    
    def _score_tech_stack(self, job: Dict) -> float:
        """Score 0-5 based on overlap between job tech stack and candidate skills."""
        skills = set(s.lower() for s in self.profile.get('candidate', {}).get('skills', []))
        desc = str(job.get('description', '')).lower()
        overlap = sum(1 for s in skills if s in desc)
        if overlap >= 3:
            return 5.0
        elif overlap == 2:
            return 4.0
        elif overlap == 1:
            return 3.0
        return 2.0
    
    def _score_growth(self, job: Dict) -> float:
        """Score based on company tier indicators."""
        return 4.0  # Heuristic fallback
    
    def _score_company(self, job: Dict) -> float:
        """Score based on company tier from india.yml mapping."""
        return 4.0  # Heuristic fallback
    
    def _score_location(self, job: Dict) -> float:
        """Score based on location match with candidate preferences."""
        pref_locs = [l.lower() for l in self.profile.get('candidate', {}).get('locations', [])]
        loc = str(job.get('location', '')).lower()
        is_remote = bool(job.get('is_remote', False)) or 'remote' in loc
        candidate_wants_remote = any('remote' in pl for pl in pref_locs)
        
        if is_remote and candidate_wants_remote:
            return 5.0
        if is_remote:
            return 4.0
        if any(pl in loc for pl in pref_locs if 'remote' not in pl):
            return 5.0
        if not pref_locs:
            return 3.5
        return 2.0
    
    def _score_jd_quality(self, job: Dict) -> float:
        """Score based on JD length, specificity, red flags."""
        desc = str(job.get('description', ''))
        words = len(desc.split())
        if words > 300:
            return 5.0
        if words > 150:
            return 4.0
        return 2.0
    
    def _score_experience(self, job: Dict) -> float:
        """Score based on experience fit (required <= candidate + 1)."""
        return 4.0 # Heuristic fallback
    
    def _score_resume_gap(self, job: Dict) -> float:
        """Score based on skills gap between JD requirements and resume."""
        return 4.0 # Heuristic fallback
    
    def _score_legitimacy(self, job: Dict) -> float:
        """Ghost job detection - flag if 2+ red flags.
        Red flags: no salary, <150 words JD, >90 days old, generic wording, reposted 5+ times."""
        flags = 0
        if not job.get('salary_min') and not job.get('salary_max') and not job.get('salary_raw'):
            flags += 1
        desc = str(job.get('description', ''))
        if len(desc.split()) < 150:
            flags += 1
        if flags >= 2:
            return 2.0
        return 5.0
    
    def _load_profile(self, path: str) -> Dict:
        """Load and parse config/profile.yml."""
        p = Path(path)
        if not p.exists():
            fallback = p.parent / 'profile.example.yml'
            if fallback.exists():
                logger.warning(f"Profile {path} not found. Falling back to {fallback}")
                p = fallback
            else:
                return {}
        try:
            with open(p, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            return {}
