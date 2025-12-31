from __future__ import annotations

from typing import Any, Dict, Optional

from jkmem.graph_store import GraphStore
from jkmem.medical.utils import build_metadata, compact_parts
from jkmem.models import Document, Medication, MemoryMetadata, Observation, PatientProfile, SourceType


class HealthRecordService:
    def __init__(self, memory_backend: Any, graph_store: Optional[GraphStore] = None) -> None:
        self._memory = memory_backend
        self._graph = graph_store

    def upsert_profile(self, *, user_id: str, profile: PatientProfile) -> Dict[str, Any]:
        if self._graph:
            self._graph.add_patient(profile)

        summary = compact_parts(
            [
                f"name={profile.name}" if profile.name else None,
                f"dob={profile.date_of_birth}" if profile.date_of_birth else None,
                f"sex={profile.sex}" if profile.sex else None,
                f"allergies={', '.join(profile.allergies)}" if profile.allergies else None,
                f"conditions={', '.join(profile.conditions)}" if profile.conditions else None,
                f"risk_factors={', '.join(profile.risk_factors)}" if profile.risk_factors else None,
                f"summary={profile.summary}" if profile.summary else None,
            ]
        )

        metadata = build_metadata(
            user_id=user_id,
            patient_id=profile.patient_id,
            source_type=SourceType.IMPORT,
            source_id=profile.patient_id,
        )
        return self._memory.add(
            [{"role": "assistant", "content": f"PatientProfile: {summary}"}],
            user_id=user_id,
            metadata=metadata,
            infer=False,
        )

    def add_observation(self, *, user_id: str, observation: Observation) -> Dict[str, Any]:
        if self._graph:
            self._graph.add_observation(observation)

        summary = compact_parts(
            [
                f"category={observation.category.value}",
                f"name={observation.name}",
                f"value={observation.value}" if observation.value else None,
                f"value_numeric={observation.value_numeric}" if observation.value_numeric is not None else None,
                f"unit={observation.unit}" if observation.unit else None,
                f"observed_at={observation.observed_at}" if observation.observed_at else None,
            ]
        )
        metadata = build_metadata(
            user_id=user_id,
            patient_id=observation.patient_id,
            encounter_id=observation.encounter_id,
            source_type=SourceType.REPORT,
            source_id=observation.observation_id,
        )
        return self._memory.add(
            [{"role": "assistant", "content": f"Observation: {summary}"}],
            user_id=user_id,
            metadata=metadata,
            infer=False,
        )

    def add_medication(self, *, user_id: str, medication: Medication) -> Dict[str, Any]:
        if self._graph:
            self._graph.add_medication(medication)

        summary = compact_parts(
            [
                f"name={medication.name}",
                f"indication={medication.indication}" if medication.indication else None,
                f"prescriber={medication.prescriber}" if medication.prescriber else None,
                f"dose={medication.dose}" if medication.dose else None,
                f"frequency={medication.frequency}" if medication.frequency else None,
                f"route={medication.route}" if medication.route else None,
                f"status={medication.status.value}",
                f"start_date={medication.start_date}" if medication.start_date else None,
                f"end_date={medication.end_date}" if medication.end_date else None,
            ]
        )
        metadata = build_metadata(
            user_id=user_id,
            patient_id=medication.patient_id,
            encounter_id=medication.encounter_id,
            source_type=SourceType.IMPORT,
            source_id=medication.medication_id,
        )
        return self._memory.add(
            [{"role": "assistant", "content": f"Medication: {summary}"}],
            user_id=user_id,
            metadata=metadata,
            infer=False,
        )

    def add_document(self, *, user_id: str, document: Document, summary: Optional[str] = None) -> Dict[str, Any]:
        if self._graph:
            self._graph.add_document(document)

        doc_summary = summary or document.summary or ""
        content = compact_parts(
            [
                f"doc_type={document.doc_type.value}",
                f"title={document.title}" if document.title else None,
                f"summary={doc_summary}" if doc_summary else None,
                f"source_uri={document.source_uri}" if document.source_uri else None,
                f"extracted_at={document.extracted_at}" if document.extracted_at else None,
            ]
        )
        metadata = build_metadata(
            user_id=user_id,
            patient_id=document.patient_id,
            encounter_id=document.encounter_id,
            source_type=SourceType.DOCUMENT,
            source_id=document.document_id,
        )
        return self._memory.add(
            [{"role": "assistant", "content": f"Document: {content}"}],
            user_id=user_id,
            metadata=metadata,
            infer=False,
        )
