# Data Model & Schema (Phase 2)

This schema defines the backend data models used by the AI Doctor Memory System. Models are implemented in `src/jkmem/models.py` and are designed to map cleanly to mem0 metadata.

## Core Metadata (all memories)
- `user_id`, `patient_id`, `encounter_id`
- `source_type`, `source_id`, `actor_role`
- `created_at`, `updated_at` (datetime)
- `confidence` (0.0-1.0), `risk_level`
- `tags` (list), `extra` (free-form dict)
- Audit columns on all tables: `version`, `is_deleted`, `created_at`, `updated_at`

## Domain Models
- **PatientProfile**: stable patient profile info + summaries
- **Encounter**: visit-level information (type, complaint, assessment, plan); time fields are datetime
- **Observation**: vitals/labs/imaging summaries; `observed_at` is datetime
- **Medication**: medication timeline, indication, prescriber; start/end are datetime
- **Document**: source files, file hash, extracted summaries; `extracted_at` is datetime
- **MemoryItem**: normalized memory text + typed category + source refs + embedding placeholder (pgvector)

## Graph Relations (optional)
- Patient HAS_ENCOUNTER Encounter
- Encounter HAS_OBSERVATION Observation
- Encounter HAS_MEDICATION Medication
- Encounter HAS_DOCUMENT Document
- Patient TAKES_MEDICATION Medication
- Patient HAS_DOCUMENT_DIRECT Document (when no encounter)

### 节点属性
| 节点 | 核心属性 |
|------|----------|
| Patient | patient_id, name, date_of_birth, sex |
| Encounter | encounter_id, encounter_type, start_time, end_time |
| Observation | observation_id, category, name, value, value_numeric, unit |
| Medication | medication_id, name, status, start_date, end_date |
| Document | document_id, doc_type, title, extracted_at |

### 关系类型
| 关系 | 方向 | 属性 |
|------|------|------|
| HAS_ENCOUNTER | Patient → Encounter | created_at |
| HAS_OBSERVATION | Encounter → Observation | - |
| HAS_MEDICATION | Encounter → Medication | - |
| TAKES_MEDICATION | Patient → Medication | prescribed_at, indication |
| HAS_DOCUMENT | Encounter → Document | - |
| HAS_DOCUMENT_DIRECT | Patient → Document | - |

### 典型查询场景
1. 查询患者所有活跃用药
2. 查询某次就诊的完整记录（含检查、用药、文档）
3. 药物相互作用检测
4. 患者病史时间线

## Enumerations
- `SourceType`: chat/report/document/import
- `ActorRole`: patient/clinician/assistant/system
- `RiskLevel`: low/medium/high
- `ObservationCategory`: vital/lab/imaging/note
- `MedicationStatus`: active/stopped/unknown
- `MemoryKind`: profile/encounter/observation/medication/document/summary
- `DocumentType`: report/prescription/lab/imaging/discharge/note/other
