import logging
import re
from typing import List, Dict, Set

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed. JobDeduplicator will fall back to exact-match only.")

class JobDeduplicator:
    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold
    
    def deduplicate(self, jobs: List[Dict]) -> List[Dict]:
        """Two-pass deduplication.
        Pass 1: Exact hash match on normalized(company + title + location)
        Pass 2: TF-IDF cosine similarity on title+company for fuzzy matching
        
        For duplicates, merge metadata:
        - Keep the entry with the longest description
        - Preserve all source URLs in a 'source_urls' list
        - Keep salary data if any entry has it
        - Keep the earliest date_posted
        """
        if not jobs:
            return []

        # Pass 1: Exact match
        exact_groups = {}
        for job in jobs:
            company = job.get('company', '')
            title = job.get('title', job.get('role', ''))
            key = self._normalize_key(company, title)
            if key not in exact_groups:
                exact_groups[key] = []
            exact_groups[key].append(job)
        
        pass_1_results = [self._merge_duplicates(group) for group in exact_groups.values()]
        
        # Pass 2: Fuzzy match
        if not SKLEARN_AVAILABLE or len(pass_1_results) < 2:
            return pass_1_results
            
        fuzzy_clusters = self._fuzzy_match(pass_1_results)
        
        final_results = []
        seen = set()
        for cluster in fuzzy_clusters:
            group = [pass_1_results[i] for i in cluster]
            final_results.append(self._merge_duplicates(group))
            seen.update(cluster)
            
        for i, job in enumerate(pass_1_results):
            if i not in seen:
                final_results.append(job)
                
        return final_results
    
    def _normalize_key(self, company: str, title: str) -> str:
        """Normalize company and title for exact matching.
        Lowercase, strip whitespace, remove common suffixes (Inc, Ltd, Pvt, Private Limited, Technologies, etc.)"""
        s = f"{company} {title}".lower()
        s = re.sub(r'\b(inc|ltd|pvt|private limited|technologies|corp|llc|co)\b', '', s)
        s = re.sub(r'[^a-z0-9]', ' ', s)
        return ' '.join(s.split())
    
    def _fuzzy_match(self, jobs: List[Dict]) -> List[List[int]]:
        """Use TF-IDF + cosine similarity to find near-duplicate clusters."""
        texts = []
        for job in jobs:
            company = job.get('company', '')
            title = job.get('title', job.get('role', ''))
            texts.append(f"{company} {title}".lower())
            
        vectorizer = TfidfVectorizer(stop_words='english', analyzer='char_wb', ngram_range=(3,5))
        tfidf = vectorizer.fit_transform(texts)
        similarity = cosine_similarity(tfidf)
        
        clusters = []
        seen = set()
        
        for i in range(len(jobs)):
            if i in seen:
                continue
            cluster = [i]
            seen.add(i)
            for j in range(i + 1, len(jobs)):
                if j not in seen and similarity[i, j] >= self.threshold:
                    cluster.append(j)
                    seen.add(j)
            if len(cluster) > 1:
                clusters.append(cluster)
                
        return clusters
    
    def _merge_duplicates(self, group: List[Dict]) -> Dict:
        """Merge a group of duplicate jobs into one canonical entry."""
        if len(group) == 1:
            job = group[0].copy()
            if 'source_urls' not in job:
                job['source_urls'] = [job.get('url')] if job.get('url') else []
            return job
            
        # Keep longest description
        group_with_desc = sorted(group, key=lambda x: len(str(x.get('description', ''))), reverse=True)
        merged = group_with_desc[0].copy()
        
        # Merge source urls
        urls = set()
        for j in group:
            if j.get('job_url'):
                urls.add(j['job_url'])
            if 'source_urls' in j:
                urls.update(j['source_urls'])
        merged['source_urls'] = list(urls)
        
        # Keep earliest date_posted
        dates = [j.get('date_posted') for j in group if j.get('date_posted')]
        if dates:
            merged['date_posted'] = min(dates)
            
        # Keep salary data if any entry has it
        for j in group:
            if j.get('salary_min') and not merged.get('salary_min'):
                merged['salary_min'] = j['salary_min']
                merged['salary_max'] = j.get('salary_max')
                merged['salary_raw'] = j.get('salary_raw')
                break
            
        return merged
