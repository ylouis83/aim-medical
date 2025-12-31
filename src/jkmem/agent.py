from typing import Any, Callable, Dict, List, Optional

Message = Dict[str, str]


def _format_memories(memories: Any) -> str:
    if isinstance(memories, dict):
        results = memories.get("results", [])
    elif isinstance(memories, list):
        results = memories
    else:
        results = []

    lines = []
    for entry in results:
        if isinstance(entry, dict):
            text = entry.get("memory") or entry.get("data") or entry.get("text")
        else:
            text = str(entry)
        if text:
            lines.append(f"- {text}")

    return "\n".join(lines) if lines else "- (none)"


class MemoryAgent:
    def __init__(self, memory: Any, llm_fn: Callable[[str, str], str]) -> None:
        self._memory = memory
        self._llm_fn = llm_fn

    def respond(
        self,
        message: str,
        user_id: str = "default",
        *,
        metadata: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        memories = self._memory.search(
            query=message, user_id=user_id, limit=3, filters=filters or None
        )
        memories_text = _format_memories(memories)
        system_prompt = (
            "You are a helpful agent. Use the memories when relevant.\n"
            f"Memories:\n{memories_text}"
        )
        response = self._llm_fn(system_prompt, message)
        self._memory.add(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response},
            ],
            user_id=user_id,
            metadata=metadata,
        )
        return {
            "content": response,
            "memories": memories.get("results", []) if isinstance(memories, dict) else memories
        }
