# Phase 1 Plan - AI Doctor Memory System (jkmem)

## Objectives
- Understand mem0 architecture, extension points, and storage options.
- Identify healthcare memory system best practices and constraints.
- Produce an implementation plan and a design proposal for approval.

## mem0 Architecture Summary (source: mem0 codebase)
- Core memory object: `mem0.memory.main.Memory` orchestrates LLM, embedder, vector store, and history DB.
- Configuration entrypoint: `mem0.configs.base.MemoryConfig` (LLM, embedder, vector store, graph store, history DB, reranker).
- Memory types: semantic, episodic, procedural (`mem0.configs.enums.MemoryType`).
- Storage:
  - Vector store interface via `VectorStoreFactory` with multiple providers (qdrant, chroma, pgvector, redis, etc.).
  - Optional graph store via `GraphStoreFactory` (neo4j, memgraph, neptune, kuzu).
  - History DB uses SQLite to track memory mutations (`mem0.memory.storage.SQLiteManager`).
- Retrieval pipeline: embed + search; supports filters/metadata; optional reranker.
- Update pipeline: LLM prompt-based memory extraction/update; history tracked.

## Healthcare Memory System Best Practices (summary)
- Data minimization: store only clinically relevant facts and summaries; avoid raw transcripts where possible.
- PHI/PII handling: encrypt at rest and in transit; strict access control and audit logging.
- Consent + retention: explicit user consent, configurable retention policies, data deletion workflows.
- Provenance + traceability: store source document IDs, timestamps, and author/actor metadata.
- Safety + reliability: clear separation of patient statements vs. clinician judgments; flag uncertainties.
- Schema discipline: use structured entities for patient profile, encounters, observations, medications, labs.
- Security boundaries: isolate per-user/patient memory namespaces; avoid cross-user leakage.

## Deliverables (Phase 1)
- Implementation plan document (this file).
- Design proposal for jkmem (docs/design_proposal.md).

## Open Questions (for approval)
- Target deployment: local-only vs. cloud service?
- Preferred vector store and graph store (if any) for initial build?
- Retention policy and data deletion requirements?
- Do we need multi-tenant access control now or later?
