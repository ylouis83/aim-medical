from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from jkmem.graph_store import GraphStore
from jkmem.medical.utils import build_metadata
from jkmem.models import Encounter, MemoryMetadata, PatientProfile, SourceType


class ConsultationService:
    def __init__(self, memory_backend: Any, graph_store: Optional[GraphStore] = None) -> None:
        self._memory = memory_backend
        self._graph = graph_store

    def log_consultation(
        self,
        *,
        user_id: str,
        patient_id: str,
        encounter_id: str,
        encounter_type: str,
        messages: List[Dict[str, str]],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        summary: Optional[str] = None,
        infer: bool = True,
    ) -> Dict[str, Any]:
        encounter = Encounter(
            encounter_id=encounter_id,
            patient_id=patient_id,
            encounter_type=encounter_type,
            start_time=start_time,
            end_time=end_time,
            metadata=MemoryMetadata(user_id=user_id, patient_id=patient_id, encounter_id=encounter_id),
        )

        if self._graph:
            profile = PatientProfile(patient_id=patient_id)
            self._graph.add_patient(profile)
            self._graph.add_encounter(encounter)

        metadata = build_metadata(
            user_id=user_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            source_type=SourceType.CHAT,
            source_id=encounter_id,
            extra={"encounter_type": encounter_type},
        )

        if summary:
            summary_messages = [{"role": "assistant", "content": summary}]
            return self._memory.add(
                summary_messages,
                user_id=user_id,
                metadata=metadata,
                infer=False,
            )

        return self._memory.add(
            messages,
            user_id=user_id,
            metadata=metadata,
            infer=infer,
        )
