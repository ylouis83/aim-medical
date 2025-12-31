from __future__ import annotations

from typing import Any, Dict, Optional

from jkmem.graph_store import GraphStore
from jkmem.medical.utils import build_metadata, compact_parts
from jkmem.models import Document, SourceType


class DocumentInterpreterService:
    def __init__(self, memory_backend: Any, graph_store: Optional[GraphStore] = None) -> None:
        self._memory = memory_backend
        self._graph = graph_store

    def store_interpretation(
        self,
        *,
        user_id: str,
        document: Document,
        summary: str,
        key_findings: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self._graph:
            self._graph.add_document(document)

        content = compact_parts(
            [
                f"doc_type={document.doc_type.value}",
                f"title={document.title}" if document.title else None,
                f"summary={summary}",
                f"key_findings={key_findings}" if key_findings else None,
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
            [{"role": "assistant", "content": f"DocumentInterpretation: {content}"}],
            user_id=user_id,
            metadata=metadata,
            infer=False,
        )
