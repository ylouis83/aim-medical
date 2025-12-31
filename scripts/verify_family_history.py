#!/usr/bin/env python3
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"

SRC_PATH = str(ROOT / "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex((host, port)) == 0


def wait_for_health(url: str, timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def post_json(url: str, payload: dict, timeout_seconds: int = 120) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def stop_process(proc: subprocess.Popen, timeout_seconds: int = 10) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout_seconds)


def main() -> int:
    load_env(ENV_PATH)

    host = "127.0.0.1"
    port = 8000
    if port_in_use(host, port):
        print(f"Port {port} is already in use; stop the running server and retry.")
        return 1

    mem0_dir = ROOT / "data" / "mem0"
    qdrant_path = ROOT / "data" / "vector" / "qdrant"
    graph_path = ROOT / "data" / "graph" / "kuzu.db"
    mem0_dir.mkdir(parents=True, exist_ok=True)
    qdrant_path.mkdir(parents=True, exist_ok=True)
    graph_path.parent.mkdir(parents=True, exist_ok=True)

    if not (os.getenv("JKMEM_BAILIAN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")):
        print("Missing JKMEM_BAILIAN_API_KEY (or DASHSCOPE_API_KEY).")
        return 1

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT / "src"),
            "MEM0_DIR": str(mem0_dir),
            "MEM0_TELEMETRY": "0",
            "JKMEM_USE_MEM0": "1",
            "JKMEM_USE_SQLITE": "0",
            "JKMEM_VECTOR_PROVIDER": "qdrant",
            "JKMEM_QDRANT_PATH": str(qdrant_path),
            "JKMEM_QDRANT_ON_DISK": "1",
            "JKMEM_GRAPH_ENABLED": "1",
            "JKMEM_GRAPH_PROVIDER": "kuzu",
            "JKMEM_GRAPH_PATH": str(graph_path),
            "JKMEM_BAILIAN_EMBEDDING_MODEL": os.getenv(
                "JKMEM_BAILIAN_EMBEDDING_MODEL", "text-embedding-v2"
            ),
            "JKMEM_HOST": host,
            "JKMEM_PORT": str(port),
        }
    )

    log_path = Path("/tmp/jkmem_family_history_verify.log")
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "src" / "jkmem" / "server.py")],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

    try:
        if not wait_for_health(f"http://{host}:{port}/health", timeout_seconds=60):
            print(f"Backend failed to start. See log: {log_path}")
            return 1

        user_id = f"family_test_{int(time.time())}"
        patient_id = f"patient_{user_id}"
        report_text = (
            "FamilyHistory: 父亲有高血压\n"
            "GeneticHistory: BRCA1 突变\n"
            "Allergy: 青霉素"
        )

        response = post_json(
            f"http://{host}:{port}/api/upload_report",
            {
                "report_text": report_text,
                "user_id": user_id,
                "patient_id": patient_id,
            },
            timeout_seconds=180,
        )
        if response.get("status") != "success":
            print(f"Upload failed: {response}")
            return 1
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Upload failed: {detail}")
        return 1
    finally:
        stop_process(proc)

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        import kuzu
    except Exception as exc:
        print(f"Missing dependencies for verification: {exc}")
        return 1

    client = QdrantClient(path=str(qdrant_path))
    points, _ = client.scroll(
        collection_name="jkmem_memories",
        scroll_filter=Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        ),
        limit=200,
        with_payload=True,
        with_vectors=False,
    )
    qdrant_memories = [{"id": p.id, "payload": p.payload} for p in points]

    needed = {"FamilyHistory": False, "GeneticHistory": False, "Allergy": False}
    observation_ids = []
    document_ids = []
    for item in qdrant_memories:
        payload = item.get("payload") or {}
        data = payload.get("data", "") or ""
        source_id = payload.get("source_id")
        for key in needed:
            if f"name={key}" in data or key in data:
                needed[key] = True
        if data.startswith("ReportObservation:"):
            observation_ids.append(source_id)
        if data.startswith("ReportDocument:"):
            document_ids.append(source_id)

    conn = kuzu.Connection(kuzu.Database(str(graph_path)))

    def fetch_all(query: str, params: dict) -> list:
        result = conn.execute(query, params)
        rows = []
        columns = list(result.get_column_names()) if hasattr(result, "get_column_names") else None
        while result.has_next():
            row = result.get_next()
            if isinstance(row, dict):
                rows.append(row)
            elif columns:
                rows.append(dict(zip(columns, row)))
            else:
                rows.append({"value": row})
        return rows

    kuzu_documents = []
    for doc_id in document_ids:
        if doc_id:
            kuzu_documents.extend(
                fetch_all(
                    "MATCH (d:Document) WHERE d.document_id = $doc_id RETURN d.*",
                    {"doc_id": doc_id},
                )
            )

    kuzu_observations = []
    for obs_id in observation_ids:
        if obs_id:
            kuzu_observations.extend(
                fetch_all(
                    "MATCH (o:Observation) WHERE o.observation_id = $obs_id RETURN o.*",
                    {"obs_id": obs_id},
                )
            )

    output = {
        "user_id": user_id,
        "patient_id": patient_id,
        "qdrant": {
            "count": len(qdrant_memories),
            "memories": qdrant_memories,
        },
        "kuzu": {
            "documents": kuzu_documents,
            "observations": kuzu_observations,
        },
    }

    if not all(needed.values()):
        print(json.dumps(output, ensure_ascii=False, indent=2))
        print(f"Missing expected categories: {needed}")
        return 1

    if not kuzu_documents or not kuzu_observations:
        print(json.dumps(output, ensure_ascii=False, indent=2))
        print("Missing persisted graph records in Kuzu.")
        return 1

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
