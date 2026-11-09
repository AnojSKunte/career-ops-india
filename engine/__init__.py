import logging

__all__ = []

try:
    from .deduplicator import JobDeduplicator
    __all__.append("JobDeduplicator")
except ImportError as e:
    logging.warning(f"Failed to import JobDeduplicator: {e}")

try:
    from .job_matcher import JobMatcher
    __all__.append("JobMatcher")
except ImportError as e:
    logging.warning(f"Failed to import JobMatcher: {e}")

try:
    from .aggregator import JobAggregator
    __all__.append("JobAggregator")
except ImportError as e:
    logging.warning(f"Failed to import JobAggregator: {e}")
