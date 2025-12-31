from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    CHAT = "chat"
    REPORT = "report"
    DOCUMENT = "document"
    IMPORT = "import"


class ActorRole(str, Enum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ObservationCategory(str, Enum):
    VITAL = "vital"
    LAB = "lab"
    IMAGING = "imaging"
    NOTE = "note"


class MedicationStatus(str, Enum):
    ACTIVE = "active"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class MemoryKind(str, Enum):
    PROFILE = "profile"
    ENCOUNTER = "encounter"
    OBSERVATION = "observation"
    MEDICATION = "medication"
    DOCUMENT = "document"
    SUMMARY = "summary"


class DocumentType(str, Enum):
    REPORT = "report"
    PRESCRIPTION = "prescription"
    LAB = "lab"
    IMAGING = "imaging"
    DISCHARGE = "discharge"
    NOTE = "note"
    OTHER = "other"


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SourceRef(ORMBaseModel):
    source_type: SourceType
    source_id: str
    page: Optional[int] = None
    span: Optional[str] = None


class MemoryMetadata(ORMBaseModel):
    user_id: Optional[str] = None
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    source_type: Optional[SourceType] = None
    source_id: Optional[str] = None
    actor_role: Optional[ActorRole] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    risk_level: Optional[RiskLevel] = None
    tags: List[str] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)

    def to_metadata(self) -> Dict[str, Any]:
        data = self.model_dump(exclude_none=True)
        extra = data.pop("extra", {})
        if extra:
            data.update(extra)
        return data


class PatientProfile(ORMBaseModel):
    patient_id: str
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    sex: Optional[str] = None
    identifiers: Dict[str, str] = Field(default_factory=dict)
    allergies: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)


class Encounter(ORMBaseModel):
    encounter_id: str
    patient_id: str
    encounter_type: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    chief_complaint: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    practitioner: Optional[str] = None
    facility: Optional[str] = None
    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)


class Observation(ORMBaseModel):
    observation_id: str
    patient_id: str
    encounter_id: Optional[str] = None
    category: ObservationCategory
    name: str
    value: Optional[str] = None
    value_numeric: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    observed_at: Optional[datetime] = None
    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)


class Medication(ORMBaseModel):
    medication_id: str
    patient_id: str
    encounter_id: Optional[str] = None
    name: str
    indication: Optional[str] = None
    prescriber: Optional[str] = None
    dose: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: MedicationStatus = MedicationStatus.UNKNOWN
    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)


class Document(ORMBaseModel):
    document_id: str
    patient_id: str
    encounter_id: Optional[str] = None
    doc_type: DocumentType = DocumentType.OTHER
    title: Optional[str] = None
    summary: Optional[str] = None
    source_uri: Optional[str] = None
    file_hash: Optional[str] = None
    extracted_at: Optional[datetime] = None
    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)


class MemoryItem(ORMBaseModel):
    memory_id: str
    text: str
    kind: MemoryKind
    embedding: Optional[List[float]] = None
    source_refs: List[SourceRef] = Field(default_factory=list)
    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)
