import unittest

from bootstrap import add_src_path

add_src_path()

from jkmem.agent import MemoryAgent
from jkmem.memory_backends import InMemoryBackend


def _stub_llm(system_prompt: str, user_message: str) -> str:
    return "ok"


class TestAgentE2E(unittest.TestCase):
    def test_agent_roundtrip(self) -> None:
        backend = InMemoryBackend()
        agent = MemoryAgent(backend, _stub_llm)

        response = agent.respond("Hello", user_id="user_1")
        self.assertEqual(response, "ok")

        results = backend.search("ok", user_id="user_1")
        self.assertGreaterEqual(len(results.get("results", [])), 1)


if __name__ == "__main__":
    unittest.main()
