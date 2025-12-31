from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from jkmem.models import ActorRole, MemoryMetadata, SourceType


def build_metadata(
    *,
    user_id: str,
    patient_id: Optional[str] = None,
    encounter_id: Optional[str] = None,
    source_type: Optional[SourceType] = None,
    source_id: Optional[str] = None,
    actor_role: Optional[ActorRole] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata = MemoryMetadata(
        user_id=user_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        source_type=source_type,
        source_id=source_id,
        actor_role=actor_role,
        created_at=created_at,
        updated_at=updated_at,
        extra=extra or {},
    )
    return metadata.to_metadata()


def compact_parts(parts: Iterable[Optional[str]]) -> str:
    return "; ".join(part for part in parts if part)
