import unittest

from bootstrap import add_src_path

add_src_path()

from jkmem.memory_backends import InMemoryBackend


class TestInMemoryBackend(unittest.TestCase):
    def test_add_and_search(self) -> None:
        backend = InMemoryBackend()
        backend.add(
            [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Remember this"},
            ],
            user_id="user_1",
            metadata={"patient_id": "patient_1"},
        )

        results = backend.search("remember", user_id="user_1", filters={"patient_id": "patient_1"})
        self.assertEqual(len(results.get("results", [])), 1)

        results_mismatch = backend.search("remember", user_id="user_1", filters={"patient_id": "other"})
        self.assertEqual(len(results_mismatch.get("results", [])), 0)


if __name__ == "__main__":
    unittest.main()
