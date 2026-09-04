"""
In-Memory Cache Manager
Fast LRU caching for query results, rewritten queries, and RAG answers.
"""

import time
import hashlib
from typing import Dict, Any, Optional

class MemoryCache:
    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _generate_key(self, dataset_id: str, question: str, mode: str) -> str:
        raw = f"{dataset_id}:{question.strip().lower()}:{mode.lower()}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def get(self, dataset_id: str, question: str, mode: str) -> Optional[Any]:
        key = self._generate_key(dataset_id, question, mode)
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["data"]
            else:
                del self._cache[key]
        return None

    def set(self, dataset_id: str, question: str, mode: str, data: Any):
        if len(self._cache) >= self.max_size:
            # Evict oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]
            
        key = self._generate_key(dataset_id, question, mode)
        self._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

    def clear(self):
        self._cache.clear()

global_cache = MemoryCache()
