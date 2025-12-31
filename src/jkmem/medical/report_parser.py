from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from jkmem.graph_store import GraphStore
from jkmem.medical.utils import build_metadata, compact_parts
from jkmem.models import (
    Document,
    DocumentType,
    MemoryMetadata,
    Observation,
    ObservationCategory,
    SourceType,
)


_VALUE_RE = re.compile(r"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>.*)")


class ReportParser:
    def parse(
        self,
        *,
        report_text: str,
        patient_id: str,
        encounter_id: Optional[str] = None,
        document_id: Optional[str] = None,
        doc_type: DocumentType = DocumentType.LAB,
        source_uri: Optional[str] = None,
        extracted_at: Optional[datetime] = None,
    ) -> Tuple[Document, List[Observation]]:
        document_id = document_id or str(uuid.uuid4())
        observations: List[Observation] = []

        for line in report_text.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            name, raw_value = [part.strip() for part in line.split(":", 1)]
            if not name or not raw_value:
                continue
            match = _VALUE_RE.match(raw_value)
            value = raw_value
            value_numeric = None
            unit = None
            if match:
                value = match.group("value")
                unit = match.group("unit").strip() or None
                try:
                    value_numeric = float(value)
                except ValueError:
                    value_numeric = None
            observations.append(
                Observation(
                    observation_id=str(uuid.uuid4()),
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    category=ObservationCategory.LAB,
                    name=name,
                    value=value,
                    value_numeric=value_numeric,
                    unit=unit,
                    observed_at=extracted_at,
                    metadata=MemoryMetadata(
                        patient_id=patient_id,
                        encounter_id=encounter_id,
                        source_type=SourceType.REPORT,
                        source_id=document_id,
                    ),
                )
            )

        summary = report_text.strip()[:500] if report_text else None
        document = Document(
            document_id=document_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            doc_type=doc_type,
            title=f"{doc_type.value} report",
            summary=summary,
            source_uri=source_uri,
            extracted_at=extracted_at,
            metadata=MemoryMetadata(
                patient_id=patient_id,
                encounter_id=encounter_id,
                source_type=SourceType.REPORT,
                source_id=document_id,
            ),
        )

        return document, observations


class ReportService:
    def __init__(self, memory_backend: Any, graph_store: Optional[GraphStore] = None) -> None:
        self._memory = memory_backend
        self._graph = graph_store
        self._parser = ReportParser()

    def parse_and_store(
        self,
        *,
        user_id: str,
        report_text: str,
        patient_id: str,
        encounter_id: Optional[str] = None,
        document_id: Optional[str] = None,
        doc_type: DocumentType = DocumentType.LAB,
        source_uri: Optional[str] = None,
        extracted_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        document, observations = self._parser.parse(
            report_text=report_text,
            patient_id=patient_id,
            encounter_id=encounter_id,
            document_id=document_id,
            doc_type=doc_type,
            source_uri=source_uri,
            extracted_at=extracted_at,
        )

        if self._graph:
            self._graph.add_document(document)
            for observation in observations:
                self._graph.add_observation(observation)

        stored = {"document_id": document.document_id, "observations": len(observations)}

        doc_metadata = build_metadata(
            user_id=user_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            source_type=SourceType.REPORT,
            source_id=document.document_id,
        )
        doc_summary = compact_parts(
            [
                f"doc_type={document.doc_type.value}",
                f"title={document.title}" if document.title else None,
                f"summary={document.summary}" if document.summary else None,
            ]
        )
        self._memory.add(
            [{"role": "assistant", "content": f"ReportDocument: {doc_summary}"}],
            user_id=user_id,
            metadata=doc_metadata,
            infer=False,
        )

        for observation in observations:
            obs_summary = compact_parts(
                [
                    f"name={observation.name}",
                    f"value={observation.value}" if observation.value else None,
                    f"value_numeric={observation.value_numeric}" if observation.value_numeric is not None else None,
                    f"unit={observation.unit}" if observation.unit else None,
                ]
            )
            obs_metadata = build_metadata(
                user_id=user_id,
                patient_id=patient_id,
                encounter_id=encounter_id,
                source_type=SourceType.REPORT,
                source_id=observation.observation_id,
            )
            self._memory.add(
                [{"role": "assistant", "content": f"ReportObservation: {obs_summary}"}],
                user_id=user_id,
                metadata=obs_metadata,
                infer=False,
            )

        return stored
