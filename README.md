# jkmem

Agent-based memory project scaffold that vendors mem0 as a submodule and provides a minimal local runtime.

## What's included
- `third_party/mem0`: mem0 upstream source (git submodule)
- `src/jkmem`: minimal agent + memory backend scaffold
- `.venv`: local Python environment (created)

## Quick start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
python -m jkmem.main
```

## Use mem0 backend
By default the sample uses an in-memory fallback so it runs offline. To switch to mem0, set:

```bash
export JKMEM_USE_MEM0=1
```

The default persistent profile uses:
- Qdrant (local, on-disk) for vectors
- Kuzu (local file) for the graph

```bash
export JKMEM_USE_MEM0=1
export JKMEM_VECTOR_PROVIDER=qdrant
export JKMEM_QDRANT_PATH=data/vector/qdrant
export JKMEM_QDRANT_ON_DISK=1
export JKMEM_GRAPH_ENABLED=1
export JKMEM_GRAPH_PROVIDER=kuzu
export JKMEM_GRAPH_PATH=data/graph/kuzu.db
```

Remote Qdrant is also supported via `JKMEM_QDRANT_HOST`/`JKMEM_QDRANT_PORT` or `JKMEM_QDRANT_URL` + `JKMEM_QDRANT_API_KEY`.
You'll also need any API keys required by your mem0 configuration. See the mem0 docs at `third_party/mem0/README.md`.

To force non-mem0 backends:
```bash
export JKMEM_USE_MEM0=0
export JKMEM_USE_SQLITE=1  # optional sqlite fallback
```

## Next steps
- Wire a real LLM call in `src/jkmem/llm.py`.
- Configure mem0 vector store + LLM in `src/jkmem/memory_backends.py` when enabling mem0.
