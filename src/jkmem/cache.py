import json
import os
import sqlite3
import threading
import time
from collections import OrderedDict
from typing import Any, Optional


class LruCache:
    def __init__(self, capacity: int = 512, ttl_seconds: int = 300) -> None:
        self._capacity = max(1, capacity)
        self._ttl_seconds = max(0, ttl_seconds)
        self._data: OrderedDict[str, tuple[Optional[float], Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at is not None and expires_at <= now:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        expires_at = None
        if self._ttl_seconds > 0:
            expires_at = time.monotonic() + self._ttl_seconds
        with self._lock:
            self._data[key] = (expires_at, value)
            self._data.move_to_end(key)
            if len(self._data) > self._capacity:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class SqliteCache:
    def __init__(self, path: str, ttl_seconds: int = 900) -> None:
        self._path = path
        self._ttl_seconds = max(0, ttl_seconds)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._lock = threading.Lock()
        self._init_table()

    def _init_table(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    cache_value TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    ttl_seconds INTEGER NOT NULL
                )
                """
            )
            self._conn.commit()

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT cache_value, updated_at, ttl_seconds
                FROM cache_entries
                WHERE cache_key = ?
                """,
                (key,),
            )
            row = cur.fetchone()
            if not row:
                return None
            value_json, updated_at, ttl_seconds = row
            if ttl_seconds > 0 and updated_at + ttl_seconds <= now:
                self._conn.execute("DELETE FROM cache_entries WHERE cache_key = ?", (key,))
                self._conn.commit()
                return None
            try:
                return json.loads(value_json)
            except json.JSONDecodeError:
                return None

    def set(self, key: str, value: Any) -> None:
        payload = json.dumps(value, default=str)
        now = time.time()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO cache_entries (cache_key, cache_value, updated_at, ttl_seconds)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    cache_value = excluded.cache_value,
                    updated_at = excluded.updated_at,
                    ttl_seconds = excluded.ttl_seconds
                """,
                (key, payload, now, self._ttl_seconds),
            )
            self._conn.commit()

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM cache_entries")
            self._conn.commit()


class MultiLevelCache:
    def __init__(self, l1: LruCache, l2: Optional[SqliteCache] = None) -> None:
        self._l1 = l1
        self._l2 = l2

    def get(self, key: str) -> Optional[Any]:
        value = self._l1.get(key)
        if value is not None:
            return value
        if self._l2 is None:
            return None
        value = self._l2.get(key)
        if value is not None:
            self._l1.set(key, value)
        return value

    def set(self, key: str, value: Any) -> None:
        self._l1.set(key, value)
        if self._l2 is not None:
            self._l2.set(key, value)

    def clear(self) -> None:
        self._l1.clear()
        if self._l2 is not None:
            self._l2.clear()
