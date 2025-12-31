import os
import tempfile
import time
import unittest

from bootstrap import add_src_path

add_src_path()

from jkmem.cache import LruCache, MultiLevelCache, SqliteCache


class TestLruCache(unittest.TestCase):
    def test_set_get_and_evict(self) -> None:
        cache = LruCache(capacity=2, ttl_seconds=10)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("c"), 3)

    def test_ttl_expiry(self) -> None:
        cache = LruCache(capacity=1, ttl_seconds=1)
        cache.set("a", 1)
        time.sleep(1.1)
        self.assertIsNone(cache.get("a"))


class TestSqliteCache(unittest.TestCase):
    def test_set_get(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cache.db")
            cache = SqliteCache(path, ttl_seconds=60)
            cache.set("k", {"v": 1})
            self.assertEqual(cache.get("k"), {"v": 1})

    def test_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cache.db")
            cache = SqliteCache(path, ttl_seconds=1)
            cache.set("k", {"v": 1})
            time.sleep(1.1)
            self.assertIsNone(cache.get("k"))


class TestMultiLevelCache(unittest.TestCase):
    def test_l2_warmup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cache.db")
            l1 = LruCache(capacity=2, ttl_seconds=60)
            l2 = SqliteCache(path, ttl_seconds=60)
            cache = MultiLevelCache(l1, l2)
            cache.set("k", {"v": 2})

            l1.clear()
            self.assertEqual(cache.get("k"), {"v": 2})
            self.assertEqual(l1.get("k"), {"v": 2})


if __name__ == "__main__":
    unittest.main()
