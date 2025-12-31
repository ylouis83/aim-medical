# aim-medical (v1.0)

AI medical memory system with a FastAPI backend, mem0 persistence (Qdrant + Kuzu), and a React frontend.

## What's included
- `src/jkmem`: backend (FastAPI + memory layer)
- `frontend/askbob-web`: React + Vite frontend
- `third_party/mem0`: mem0 upstream source (git submodule)
- `scripts/verify_family_history.py`: one-click persistence verification

## Quick start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
cp .env.example .env
# set JKMEM_BAILIAN_API_KEY in .env
```

## Backend (mem0 persistent profile)
The default persistent profile uses:
- Qdrant (local, on-disk) for vectors
- Kuzu (local file) for the graph

```bash
export JKMEM_USE_MEM0=1
export JKMEM_USE_MEM0=1
export JKMEM_VECTOR_PROVIDER=qdrant
export JKMEM_QDRANT_PATH=data/vector/qdrant
export JKMEM_QDRANT_ON_DISK=1
export JKMEM_GRAPH_ENABLED=1
export JKMEM_GRAPH_PROVIDER=kuzu
export JKMEM_GRAPH_PATH=data/graph/kuzu.db
export MEM0_DIR=data/mem0
export JKMEM_BAILIAN_EMBEDDING_MODEL=text-embedding-v2
python -m jkmem.server
```

Remote Qdrant is also supported via `JKMEM_QDRANT_HOST`/`JKMEM_QDRANT_PORT` or `JKMEM_QDRANT_URL` + `JKMEM_QDRANT_API_KEY`.
You'll also need any API keys required by your mem0 configuration. See the mem0 docs at `third_party/mem0/README.md`.

To force non-mem0 backends:
```bash
export JKMEM_USE_MEM0=0
export JKMEM_USE_SQLITE=1  # optional sqlite fallback
```

## Frontend
```bash
cd frontend/askbob-web
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:8000`.

## One-click persistence verification
```bash
/path/to/venv/bin/python scripts/verify_family_history.py
```

## Release
Current release: `v1.0`.
