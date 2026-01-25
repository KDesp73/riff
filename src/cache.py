import os
import time
import pickle
import threading
from typing import Any, Dict, Tuple, Optional


CacheEntry = Tuple[float, Any]


class Cache:
    def __init__(
        self,
        path: str,
        ttl: int = 60 * 60 * 24 * 3,  # 3 days
    ):
        self.path = os.path.expanduser(path)
        self.ttl = ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

        self._load()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None

            ts, value = entry
            if time.time() - ts > self.ttl:
                del self._cache[key]
                self._store()
                return None

            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = (time.time(), value)
            self._store()

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._store()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return

        try:
            with open(self.path, "rb") as f:
                data = pickle.load(f)
                if isinstance(data, dict):
                    self._cache = data
        except Exception:
            # Corrupt cache → ignore
            self._cache = {}

    def _store(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"

        with open(tmp, "wb") as f:
            pickle.dump(self._cache, f)

        os.replace(tmp, self.path)
