import os
import tempfile
import unittest

from bootstrap import add_src_path

add_src_path()

from jkmem.graph_store import KuzuGraphStore


try:
    import kuzu  # noqa: F401
    KUZU_AVAILABLE = True
except Exception:
    KUZU_AVAILABLE = False


@unittest.skipUnless(KUZU_AVAILABLE, "kuzu not installed")
class TestKuzuGraphStore(unittest.TestCase):
    def test_init_and_close(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "graph.kuzu")
            store = KuzuGraphStore(path)
            store.close()


if __name__ == "__main__":
    unittest.main()
