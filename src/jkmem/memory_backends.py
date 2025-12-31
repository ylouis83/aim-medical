import hashlib
import json
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from jkmem.cache import LruCache, MultiLevelCache, SqliteCache
from jkmem.mem0_config import build_mem0_config


class InMemoryBackend:
    def __init__(self) -> None:
        self._entries: List[Dict[str, str]] = []

    def add(
        self,
        messages: List[Dict[str, str]],
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> None:
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if content:
                    entry: Dict[str, Any] = {"user_id": user_id, "memory": content}
                    if metadata:
                        entry.update(metadata)
                    self._entries.append(entry)

    def search(
        self,
        query: str,
        user_id: str = "default",
        limit: int = 3,
        filters: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        # Simple simplistic "semantic" search:
        # 1. Exact/Substring matches first
        # 2. If few matches, include recent conversation history as "Short Term Memory"
        
        query_lower = query.lower()
        matches = []
        user_entries = [e for e in self._entries if e.get("user_id") == user_id]
        
        # 1. Search content
        for entry in user_entries:
            if filters:
                if any(entry.get(key) != value for key, value in filters.items()):
                    continue
            
            # Substring match
            if query_lower in entry["memory"].lower():
                matches.append(entry)
        
        # 2. Fallback / Fill up with recent if we have space (Simulation of Context)
        # In a real vector DB, we'd always get results.
        # Here we simulate "Relevant Context" by grabbing recent items if specific search fails.
        if len(matches) < limit:
             # Get recent entries that aren't already matched
             # Reverse to get most recent
             for entry in reversed(user_entries):
                if entry not in matches:
                    matches.append(entry)
                    if len(matches) >= limit:
                        break
        
        return {"results": matches[:limit]}


class SqliteBackend:
    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or _resolve_sqlite_path()
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    memory TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add(
        self,
        messages: List[Dict[str, str]],
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> None:
        entries = []
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if content:
                    entries.append((user_id, content, json.dumps(metadata or {})))
        if not entries:
            return
        with self._lock:
            with self._connect() as conn:
                conn.executemany(
                    "INSERT INTO memory_entries (user_id, memory, metadata) VALUES (?, ?, ?)",
                    entries,
                )

    def search(
        self,
        query: str,
        user_id: str = "default",
        limit: int = 3,
        filters: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        query_lower = query.lower()
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT id, user_id, memory, metadata FROM memory_entries WHERE user_id = ? ORDER BY id",
                    (user_id,),
                ).fetchall()

        entries: List[Dict[str, Any]] = []
        for _, row_user, memory, metadata_raw in rows:
            metadata_obj: Dict[str, Any] = {}
            if metadata_raw:
                try:
                    metadata_obj = json.loads(metadata_raw)
                except json.JSONDecodeError:
                    metadata_obj = {}
            entry: Dict[str, Any] = {"user_id": row_user, "memory": memory, "metadata": metadata_obj}
            entry.update(metadata_obj)
            entries.append(entry)

        if filters:
            entries = [
                entry
                for entry in entries
                if all(entry.get(key) == value for key, value in filters.items())
            ]

        matches = [entry for entry in entries if query_lower in entry["memory"].lower()]

        if len(matches) < limit:
            for entry in reversed(entries):
                if entry not in matches:
                    matches.append(entry)
                    if len(matches) >= limit:
                        break

        return {"results": matches[:limit]}


class Mem0Backend:
    def __init__(self) -> None:
        from mem0 import Memory

        self._memory = Memory(config=build_mem0_config())
        self._cache = _build_cache()

    def add(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        result = self._memory.add(messages, user_id=user_id, metadata=metadata, **kwargs)
        if self._cache:
            self._cache.clear()
        return result

    def search(
        self,
        query: str,
        user_id: str,
        limit: int = 3,
        filters: Optional[Dict[str, Any]] = None,
        threshold: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        cache_key = None
        if self._cache:
            cache_key = _build_cache_key(
                query=query,
                user_id=user_id,
                limit=limit,
                filters=filters,
                threshold=threshold,
                extra=kwargs,
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
        result = self._memory.search(
            query,
            user_id=user_id,
            limit=limit,
            filters=filters,
            threshold=threshold,
            **kwargs,
        )
        if self._cache and cache_key:
            self._cache.set(cache_key, result)
        return result


def _build_cache_key(
    *, query: str, user_id: str, limit: int, filters: Optional[Dict[str, Any]], threshold: Optional[float], extra: Dict[str, Any]
) -> str:
    payload = {
        "query": query,
        "user_id": user_id,
        "limit": limit,
        "filters": filters or {},
        "threshold": threshold,
        "extra": extra,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _build_cache() -> Optional[MultiLevelCache]:
    if os.getenv("JKMEM_CACHE_ENABLED", "1") != "1":
        return None
    l1_capacity = int(os.getenv("JKMEM_CACHE_L1_CAPACITY", "512"))
    l1_ttl = int(os.getenv("JKMEM_CACHE_L1_TTL", "300"))
    l1 = LruCache(capacity=l1_capacity, ttl_seconds=l1_ttl)

    l2_path = os.getenv("JKMEM_CACHE_L2_PATH", "data/cache/search_cache.db")
    l2_ttl = int(os.getenv("JKMEM_CACHE_L2_TTL", "900"))
    l2 = None
    if os.getenv("JKMEM_CACHE_L2_ENABLED", "1") == "1":
        l2 = SqliteCache(l2_path, ttl_seconds=l2_ttl)
    return MultiLevelCache(l1, l2)


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _resolve_sqlite_path() -> str:
    default_path = os.path.join(_project_root(), "data", "memory", "memories.db")
    path = os.getenv("JKMEM_SQLITE_PATH", default_path)
    if not os.path.isabs(path):
        path = os.path.join(_project_root(), path)
    return path


def get_memory_backend() -> Any:
    if os.getenv("JKMEM_USE_SQLITE") == "1":
        return SqliteBackend()

    if os.getenv("JKMEM_USE_MEM0", "1") == "1":
        try:
            return Mem0Backend()
        except Exception as exc:
            raise RuntimeError(
                "mem0 backend requested but mem0 is not installed or configured. "
                "Run `pip install -r requirements.txt` and set mem0 env vars."
            ) from exc

    return InMemoryBackend()
