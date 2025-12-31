# Design Proposal - AI Doctor Memory System (jkmem)

## Goals
- Provide a memory layer for a medical AI assistant that is safe, auditable, and personalized.
- Use mem0 as the memory engine with configurable vector and graph storage.
- Support clinical workflows: online consult, report parsing, health records, and document interpretation.

## Non-Goals (Phase 1)
- Full EMR integration or FHIR server parity.
- Advanced UI or multi-channel client apps.
- Regulatory compliance certification (we will design for compliance, not certify).

## High-Level Architecture
- **CUI Agent** (Phase 5): CLI interface for user conversations.
- **Memory Service** (core): orchestrates mem0, data schema, and domain logic.
- **Ingestion Pipelines**: parse reports, normalize entities, create memories.
- **Storage**:
  - Vector store for semantic retrieval.
  - Graph store for relationships (conditions, meds, labs, timeline).
  - History DB for changes and audit trail.

## Data Model (initial)
- **PatientProfile**: demographics, identifiers, risk factors (minimal scope).
- **Encounter**: visit metadata, complaints, assessment, plan.
- **Observation**: vitals, labs, imaging summaries.
- **Medication**: name, dose, frequency, start/end.
- **Document**: source, type, extracted summary, provenance.
- **MemoryItem**: normalized medical fact with type, confidence, source refs.

Metadata fields to include on every memory item:
- `user_id`, `patient_id`, `encounter_id`
- `source_type` (chat/report/doc), `source_id`
- `created_at`, `updated_at`, `actor_role` (patient/doctor/assistant)
- `confidence`, `risk_level`

## Retrieval Strategy
- Combine semantic vector search with metadata filters (patient_id, encounter_id).
- Use graph queries for relationship-heavy questions (medication interactions, condition history).
- Apply reranker only for long queries or ambiguous retrieval.

## Safety and Compliance Controls
- Namespace isolation by `patient_id` / `user_id`.
- Data minimization (store summaries, not raw transcripts by default).
- Encryption at rest/in transit (deployment-specific).
- Audit log via history DB, with explicit delete/rectify flows.

## Phase Plan (Execution)
- Phase 2: project structure, mem0 dependency, schema definitions.
- Phase 3: implement medical memory structures, vector DB config, graph DB config, caching.
- Phase 4: domain modules (consult, report, health records, doc interpretation).
- Phase 5: CLI interface + retrieval integration.
- Phase 6: unit/integration/E2E tests.

## Decisions Needed for Approval
- Which vector store (qdrant default vs. pgvector/redis)?
- Which graph store (neo4j vs. kuzu)?
- Retention policy and data deletion requirements.
- Whether to persist raw documents or only structured summaries.
