import shlex
from typing import Any, Dict, Optional

from jkmem.agent import MemoryAgent
from jkmem.graph_store import get_graph_store
from jkmem.llm import call_llm
from jkmem.memory_backends import get_memory_backend


class JkMemCli:
    def __init__(self, memory_backend: Any) -> None:
        self._memory = memory_backend
        self._agent = MemoryAgent(memory_backend, call_llm)
        self._graph = get_graph_store()
        self._user_id = "default"
        self._patient_id: Optional[str] = None
        self._encounter_id: Optional[str] = None

    def run(self) -> None:
        print("JKMem CLI ready. Type /help for commands.")
        while True:
            try:
                line = input("jkmem> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line.startswith("/"):
                if not self._handle_command(line):
                    break
                continue
            self._chat(line)

        if self._graph:
            self._graph.close()

    def _chat(self, message: str) -> None:
        metadata = self._build_metadata()
        filters = self._build_filters()
        response = self._agent.respond(
            message,
            user_id=self._user_id,
            metadata=metadata,
            filters=filters,
        )
        print(f"assistant: {response}")

    def _handle_command(self, line: str) -> bool:
        tokens = shlex.split(line)
        command = tokens[0].lower()
        args = tokens[1:]

        if command in {"/exit", "/quit"}:
            return False
        if command == "/help":
            self._print_help()
            return True
        if command == "/use":
            return self._cmd_use(args)
        if command == "/context":
            self._print_context()
            return True
        if command == "/search":
            self._cmd_search(args)
            return True
        if command == "/graph":
            self._cmd_graph(args)
            return True
        print("Unknown command. Type /help.")
        return True

    def _cmd_use(self, args: list[str]) -> bool:
        if len(args) < 2:
            print("Usage: /use <user|patient|encounter> <id>")
            return True
        key = args[0].lower()
        value = args[1]
        if key == "user":
            self._user_id = value
        elif key == "patient":
            self._patient_id = value
        elif key == "encounter":
            self._encounter_id = value
        else:
            print("Unknown scope. Use user|patient|encounter.")
        self._print_context()
        return True

    def _cmd_search(self, args: list[str]) -> None:
        query, opts = self._parse_kv_args(args)
        if not query:
            print("Usage: /search <query> [--limit N] [--user U] [--patient P] [--encounter E]")
            return
        user_id = opts.get("user", self._user_id)
        limit = int(opts.get("limit", "5"))
        filters = {}
        patient_id = opts.get("patient", self._patient_id)
        encounter_id = opts.get("encounter", self._encounter_id)
        if patient_id:
            filters["patient_id"] = patient_id
        if encounter_id:
            filters["encounter_id"] = encounter_id

        results = self._memory.search(query, user_id=user_id, limit=limit, filters=filters)
        memories = results.get("results", [])
        if not memories:
            print("No results.")
            return
        for idx, item in enumerate(memories, 1):
            memory_text = item.get("memory") or item.get("data") or ""
            score = item.get("score")
            suffix = f" (score={score:.3f})" if isinstance(score, (int, float)) else ""
            print(f"{idx}. {memory_text}{suffix}")

    def _cmd_graph(self, args: list[str]) -> None:
        if not self._graph:
            print("Graph store not enabled.")
            return
        if not args:
            print("Usage: /graph <active_meds|encounter|timeline|med_pairs> <id> [--limit N]")
            return
        action = args[0].lower()
        target = args[1] if len(args) > 1 else None
        if not target:
            print("Missing id.")
            return

        if action == "active_meds":
            rows = self._graph.get_active_medications(target)
        elif action == "encounter":
            record = self._graph.get_encounter_record(target)
            print(record)
            return
        elif action == "timeline":
            _, opts = self._parse_kv_args(args[1:])
            limit = int(opts.get("limit", "50"))
            rows = self._graph.get_patient_timeline(target, limit=limit)
        elif action == "med_pairs":
            rows = self._graph.get_medication_pairs(target)
        else:
            print("Unknown graph action.")
            return

        for row in rows:
            print(row)

    def _build_metadata(self) -> Optional[Dict[str, Any]]:
        metadata = {}
        if self._patient_id:
            metadata["patient_id"] = self._patient_id
        if self._encounter_id:
            metadata["encounter_id"] = self._encounter_id
        return metadata or None

    def _build_filters(self) -> Optional[Dict[str, Any]]:
        filters = {}
        if self._patient_id:
            filters["patient_id"] = self._patient_id
        if self._encounter_id:
            filters["encounter_id"] = self._encounter_id
        return filters or None

    def _parse_kv_args(self, args: list[str]) -> tuple[str, Dict[str, str]]:
        opts: Dict[str, str] = {}
        query_parts = []
        i = 0
        while i < len(args):
            token = args[i]
            if token.startswith("--"):
                key = token[2:]
                value = None
                if "=" in key:
                    key, value = key.split("=", 1)
                else:
                    if i + 1 < len(args):
                        value = args[i + 1]
                        i += 1
                if value is not None:
                    opts[key] = value
            else:
                query_parts.append(token)
            i += 1
        return " ".join(query_parts).strip(), opts

    def _print_context(self) -> None:
        print(
            f"user_id={self._user_id} patient_id={self._patient_id or '-'} "
            f"encounter_id={self._encounter_id or '-'}"
        )

    def _print_help(self) -> None:
        print(
            "Commands:\n"
            "  /help\n"
            "  /exit\n"
            "  /use <user|patient|encounter> <id>\n"
            "  /context\n"
            "  /search <query> [--limit N] [--user U] [--patient P] [--encounter E]\n"
            "  /graph active_meds <patient_id>\n"
            "  /graph encounter <encounter_id>\n"
            "  /graph timeline <patient_id> [--limit N]\n"
            "  /graph med_pairs <patient_id>"
        )


def main() -> None:
    memory_backend = get_memory_backend()
    cli = JkMemCli(memory_backend)
    cli.run()


if __name__ == "__main__":
    main()
