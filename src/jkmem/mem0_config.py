import os
from dataclasses import dataclass
from typing import Optional

from mem0.configs.base import MemoryConfig
from mem0.embeddings.configs import EmbedderConfig
from mem0.graphs.configs import GraphStoreConfig, KuzuConfig, MemgraphConfig, Neo4jConfig, NeptuneConfig
from mem0.llms.configs import LlmConfig
from mem0.vector_stores.configs import VectorStoreConfig


@dataclass(frozen=True)
class Mem0Env:
    api_key: Optional[str]
    base_url: str
    model: str
    temperature: float
    embedding_model: str
    embedding_dims: int


def _load_bailian_env() -> Mem0Env:
    api_key = os.getenv("JKMEM_BAILIAN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv(
        "JKMEM_BAILIAN_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    model = os.getenv("JKMEM_BAILIAN_MODEL", "qwen-plus")
    embedding_model = os.getenv("JKMEM_BAILIAN_EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dims = int(os.getenv("JKMEM_VECTOR_DIMS", "1536"))
    temperature = float(os.getenv("JKMEM_BAILIAN_TEMPERATURE", "0.2"))
    return Mem0Env(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        embedding_model=embedding_model,
        embedding_dims=embedding_dims,
    )


def _build_vector_config() -> VectorStoreConfig:
    provider = os.getenv("JKMEM_VECTOR_PROVIDER", "qdrant")
    collection = os.getenv("JKMEM_VECTOR_COLLECTION", "jkmem_memories")
    embedding_dims = int(os.getenv("JKMEM_VECTOR_DIMS", "1536"))

    if provider == "pgvector":
        conn_str = os.getenv("JKMEM_PGVECTOR_URL") or os.getenv("JKMEM_PGVECTOR_CONNECTION")
        hnsw = os.getenv("JKMEM_PGVECTOR_HNSW", "1") == "1"
        diskann = os.getenv("JKMEM_PGVECTOR_DISKANN", "0") == "1"

        if conn_str:
            config = {
                "connection_string": conn_str,
                "collection_name": collection,
                "embedding_model_dims": embedding_dims,
                "hnsw": hnsw,
                "diskann": diskann,
            }
            return VectorStoreConfig(provider=provider, config=config)

        user = os.getenv("JKMEM_PGVECTOR_USER")
        password = os.getenv("JKMEM_PGVECTOR_PASSWORD")
        host = os.getenv("JKMEM_PGVECTOR_HOST")
        port = os.getenv("JKMEM_PGVECTOR_PORT")
        dbname = os.getenv("JKMEM_PGVECTOR_DB", "postgres")

        missing = [name for name, value in {
            "JKMEM_PGVECTOR_USER": user,
            "JKMEM_PGVECTOR_PASSWORD": password,
            "JKMEM_PGVECTOR_HOST": host,
            "JKMEM_PGVECTOR_PORT": port,
        }.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing PGVector settings: "
                + ", ".join(missing)
                + ". Set JKMEM_PGVECTOR_URL or provide user/password/host/port."
            )

        config = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": int(port),
            "collection_name": collection,
            "embedding_model_dims": embedding_dims,
            "hnsw": hnsw,
            "diskann": diskann,
        }
        return VectorStoreConfig(provider=provider, config=config)

    if provider == "chroma":
        path = os.getenv("JKMEM_CHROMA_PATH", "data/vector/chroma")
        os.makedirs(path, exist_ok=True)
        return VectorStoreConfig(provider=provider, config={"path": path, "collection_name": collection})

    if provider == "qdrant":
        url = os.getenv("JKMEM_QDRANT_URL")
        api_key = os.getenv("JKMEM_QDRANT_API_KEY")
        host = os.getenv("JKMEM_QDRANT_HOST")
        port = os.getenv("JKMEM_QDRANT_PORT")
        path = os.getenv("JKMEM_QDRANT_PATH", "data/vector/qdrant")
        on_disk = os.getenv("JKMEM_QDRANT_ON_DISK", "1") == "1"

        config = {
            "collection_name": collection,
            "embedding_model_dims": embedding_dims,
            "on_disk": on_disk,
        }

        if url:
            if not api_key:
                raise RuntimeError("Missing Qdrant API key: JKMEM_QDRANT_API_KEY.")
            config.update({"url": url, "api_key": api_key})
            return VectorStoreConfig(provider=provider, config=config)

        if host or port:
            if not host or not port:
                raise RuntimeError("Missing Qdrant host/port: JKMEM_QDRANT_HOST and JKMEM_QDRANT_PORT.")
            config.update({"host": host, "port": int(port)})
            if api_key:
                config["api_key"] = api_key
            return VectorStoreConfig(provider=provider, config=config)

        os.makedirs(path, exist_ok=True)
        config["path"] = path
        return VectorStoreConfig(provider=provider, config=config)

    raise RuntimeError(f"Unsupported vector provider: {provider}")


def _build_graph_config(env: Mem0Env) -> GraphStoreConfig:
    provider = os.getenv("JKMEM_GRAPH_PROVIDER", "kuzu")
    enabled = os.getenv("JKMEM_GRAPH_ENABLED", "1") == "1"

    if not enabled:
        return GraphStoreConfig(provider=provider, config=None)

    if provider == "kuzu":
        db_path = os.getenv("JKMEM_GRAPH_PATH", "data/graph/kuzu.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return GraphStoreConfig(provider=provider, config={"db": db_path})

    if provider == "neo4j":
        url = os.getenv("JKMEM_NEO4J_URL")
        username = os.getenv("JKMEM_NEO4J_USERNAME")
        password = os.getenv("JKMEM_NEO4J_PASSWORD")
        database = os.getenv("JKMEM_NEO4J_DATABASE")
        base_label = os.getenv("JKMEM_NEO4J_BASE_LABEL", "0") == "1"
        if not url or not username or not password:
            raise RuntimeError("Missing Neo4j settings: JKMEM_NEO4J_URL/USERNAME/PASSWORD.")
        return GraphStoreConfig(
            provider=provider,
            config=Neo4jConfig(
                url=url,
                username=username,
                password=password,
                database=database,
                base_label=base_label,
            ),
        )

    if provider == "memgraph":
        url = os.getenv("JKMEM_MEMGRAPH_URL")
        username = os.getenv("JKMEM_MEMGRAPH_USERNAME")
        password = os.getenv("JKMEM_MEMGRAPH_PASSWORD")
        if not url or not username or not password:
            raise RuntimeError("Missing Memgraph settings: JKMEM_MEMGRAPH_URL/USERNAME/PASSWORD.")
        return GraphStoreConfig(
            provider=provider,
            config=MemgraphConfig(url=url, username=username, password=password),
        )

    if provider in {"neptune", "neptunedb"}:
        endpoint = os.getenv("JKMEM_NEPTUNE_ENDPOINT")
        if not endpoint:
            raise RuntimeError("Missing Neptune endpoint: JKMEM_NEPTUNE_ENDPOINT.")
        return GraphStoreConfig(provider=provider, config=NeptuneConfig(endpoint=endpoint))

    raise RuntimeError(f"Unsupported graph provider: {provider}")


def build_mem0_config() -> MemoryConfig:
    env = _load_bailian_env()
    history_path = os.getenv("JKMEM_MEM0_HISTORY_DB", "data/mem0/history.db")
    os.makedirs(os.path.dirname(history_path), exist_ok=True)

    llm = LlmConfig(
        provider="openai",
        config={
            "api_key": env.api_key,
            "openai_base_url": env.base_url,
            "model": env.model,
            "temperature": env.temperature,
        },
    )

    embedder = EmbedderConfig(
        provider="openai",
        config={
            "api_key": env.api_key,
            "openai_base_url": env.base_url,
            "model": env.embedding_model,
            "embedding_dims": env.embedding_dims,
        },
    )

    vector_store = _build_vector_config()
    graph_store = _build_graph_config(env)

    return MemoryConfig(
        vector_store=vector_store,
        llm=llm,
        embedder=embedder,
        graph_store=graph_store,
        history_db_path=history_path,
        version="v1.1",
    )
