import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from jkmem.models import Document, Encounter, Medication, Observation, PatientProfile


@dataclass(frozen=True)
class GraphConfig:
    provider: str
    enabled: bool
    kuzu_path: str
    neo4j_url: Optional[str]
    neo4j_username: Optional[str]
    neo4j_password: Optional[str]
    neo4j_database: Optional[str]
    neo4j_max_pool: int
    neo4j_acquire_timeout: int


def load_graph_config() -> GraphConfig:
    provider = os.getenv("JKMEM_GRAPH_PROVIDER", "kuzu")
    enabled = os.getenv("JKMEM_GRAPH_ENABLED", "1") == "1"
    kuzu_path = os.getenv("JKMEM_GRAPH_PATH", "data/graph/kuzu.db")
    return GraphConfig(
        provider=provider,
        enabled=enabled,
        kuzu_path=kuzu_path,
        neo4j_url=os.getenv("JKMEM_NEO4J_URL"),
        neo4j_username=os.getenv("JKMEM_NEO4J_USERNAME"),
        neo4j_password=os.getenv("JKMEM_NEO4J_PASSWORD"),
        neo4j_database=os.getenv("JKMEM_NEO4J_DATABASE"),
        neo4j_max_pool=int(os.getenv("JKMEM_NEO4J_MAX_POOL", "10")),
        neo4j_acquire_timeout=int(os.getenv("JKMEM_NEO4J_ACQUIRE_TIMEOUT", "30")),
    )


class GraphStore:
    def close(self) -> None:
        return None

    def __enter__(self) -> "GraphStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def add_patient(self, profile: PatientProfile) -> None:
        raise NotImplementedError

    def add_encounter(self, encounter: Encounter) -> None:
        raise NotImplementedError

    def add_observation(self, observation: Observation) -> None:
        raise NotImplementedError

    def add_medication(self, medication: Medication) -> None:
        raise NotImplementedError

    def add_document(self, document: Document) -> None:
        raise NotImplementedError

    def get_active_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_encounter_record(self, encounter_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def get_patient_timeline(self, patient_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_medication_pairs(self, patient_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError


class KuzuGraphStore(GraphStore):
    def __init__(self, path: str) -> None:
        try:
            import kuzu
        except ImportError as exc:
            raise RuntimeError("kuzu is not installed. Run `pip install kuzu`.") from exc

        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._db = kuzu.Database(path)
        self._conn = kuzu.Connection(self._db)
        self._init_schema()

    def _exec(self, query: str, params: Optional[dict] = None) -> None:
        if params:
            self._conn.execute(query, params)
        else:
            self._conn.execute(query)

    def _fetch(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        result = self._conn.execute(query, params or {})
        if hasattr(result, "get_as_df"):
            df = result.get_as_df()
            return df.to_dict(orient="records")
        rows: List[Dict[str, Any]] = []
        columns = []
        if hasattr(result, "get_column_names"):
            columns = list(result.get_column_names())
        while result.has_next():
            row = result.get_next()
            if isinstance(row, dict):
                rows.append(row)
            elif columns:
                rows.append(dict(zip(columns, row)))
            else:
                rows.append({"value": row})
        return rows

    def _init_schema(self) -> None:
        self._exec(
            """
            CREATE NODE TABLE IF NOT EXISTS Patient(
                patient_id STRING,
                name STRING,
                date_of_birth DATE,
                sex STRING,
                PRIMARY KEY (patient_id)
            );
            """
        )
        self._exec(
            """
            CREATE NODE TABLE IF NOT EXISTS Encounter(
                encounter_id STRING,
                encounter_type STRING,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                PRIMARY KEY (encounter_id)
            );
            """
        )
        self._exec(
            """
            CREATE NODE TABLE IF NOT EXISTS Observation(
                observation_id STRING,
                category STRING,
                name STRING,
                value STRING,
                value_numeric DOUBLE,
                unit STRING,
                observed_at TIMESTAMP,
                PRIMARY KEY (observation_id)
            );
            """
        )
        self._exec(
            """
            CREATE NODE TABLE IF NOT EXISTS Medication(
                medication_id STRING,
                name STRING,
                indication STRING,
                prescriber STRING,
                status STRING,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                PRIMARY KEY (medication_id)
            );
            """
        )
        self._exec(
            """
            CREATE NODE TABLE IF NOT EXISTS Document(
                document_id STRING,
                doc_type STRING,
                title STRING,
                extracted_at TIMESTAMP,
                PRIMARY KEY (document_id)
            );
            """
        )
        self._exec(
            "CREATE REL TABLE IF NOT EXISTS HAS_ENCOUNTER(FROM Patient TO Encounter, created_at TIMESTAMP);"
        )
        self._exec("CREATE REL TABLE IF NOT EXISTS HAS_OBSERVATION(FROM Encounter TO Observation);")
        self._exec("CREATE REL TABLE IF NOT EXISTS HAS_MEDICATION(FROM Encounter TO Medication);")
        self._exec("CREATE REL TABLE IF NOT EXISTS HAS_DOCUMENT(FROM Encounter TO Document);")
        self._exec("CREATE REL TABLE IF NOT EXISTS HAS_DOCUMENT_DIRECT(FROM Patient TO Document);")
        self._exec(
            "CREATE REL TABLE IF NOT EXISTS TAKES_MEDICATION(FROM Patient TO Medication, prescribed_at TIMESTAMP, indication STRING);"
        )

    def close(self) -> None:
        if hasattr(self._conn, "close"):
            self._conn.close()
        if hasattr(self._db, "close"):
            self._db.close()

    def add_patient(self, profile: PatientProfile) -> None:
        self._exec(
            """
            MERGE (p:Patient {patient_id: $patient_id})
            SET p.name = $name,
                p.date_of_birth = $date_of_birth,
                p.sex = $sex
            """,
            {
                "patient_id": profile.patient_id,
                "name": profile.name,
                "date_of_birth": profile.date_of_birth,
                "sex": profile.sex,
            },
        )

    def add_encounter(self, encounter: Encounter) -> None:
        created_at = encounter.metadata.created_at or encounter.start_time
        self._exec(
            """
            MERGE (e:Encounter {encounter_id: $encounter_id})
            SET e.encounter_type = $encounter_type,
                e.start_time = $start_time,
                e.end_time = $end_time
            """,
            {
                "encounter_id": encounter.encounter_id,
                "encounter_type": encounter.encounter_type,
                "start_time": encounter.start_time,
                "end_time": encounter.end_time,
            },
        )
        self._exec(
            """
            MATCH (p:Patient {patient_id: $patient_id})
            MATCH (e:Encounter {encounter_id: $encounter_id})
            MERGE (p)-[r:HAS_ENCOUNTER]->(e)
            SET r.created_at = $created_at
            """,
            {
                "patient_id": encounter.patient_id,
                "encounter_id": encounter.encounter_id,
                "created_at": created_at,
            },
        )

    def add_observation(self, observation: Observation) -> None:
        self._exec(
            """
            MERGE (o:Observation {observation_id: $observation_id})
            SET o.category = $category,
                o.name = $name,
                o.value = $value,
                o.value_numeric = $value_numeric,
                o.unit = $unit,
                o.observed_at = $observed_at
            """,
            {
                "observation_id": observation.observation_id,
                "category": observation.category.value,
                "name": observation.name,
                "value": observation.value,
                "value_numeric": observation.value_numeric,
                "unit": observation.unit,
                "observed_at": observation.observed_at,
            },
        )
        if observation.encounter_id:
            self._exec(
                """
                MATCH (e:Encounter {encounter_id: $encounter_id})
                MATCH (o:Observation {observation_id: $observation_id})
                MERGE (e)-[:HAS_OBSERVATION]->(o)
                """,
                {"encounter_id": observation.encounter_id, "observation_id": observation.observation_id},
            )

    def add_medication(self, medication: Medication) -> None:
        self._exec(
            """
            MERGE (m:Medication {medication_id: $medication_id})
            SET m.name = $name,
                m.indication = $indication,
                m.prescriber = $prescriber,
                m.status = $status,
                m.start_date = $start_date,
                m.end_date = $end_date
            """,
            {
                "medication_id": medication.medication_id,
                "name": medication.name,
                "indication": medication.indication,
                "prescriber": medication.prescriber,
                "status": medication.status.value,
                "start_date": medication.start_date,
                "end_date": medication.end_date,
            },
        )
        if medication.encounter_id:
            self._exec(
                """
                MATCH (e:Encounter {encounter_id: $encounter_id})
                MATCH (m:Medication {medication_id: $medication_id})
                MERGE (e)-[:HAS_MEDICATION]->(m)
                """,
                {"encounter_id": medication.encounter_id, "medication_id": medication.medication_id},
            )
        prescribed_at = medication.start_date or medication.metadata.created_at
        self._exec(
            """
            MATCH (p:Patient {patient_id: $patient_id})
            MATCH (m:Medication {medication_id: $medication_id})
            MERGE (p)-[r:TAKES_MEDICATION]->(m)
            SET r.prescribed_at = $prescribed_at,
                r.indication = $indication
            """,
            {
                "patient_id": medication.patient_id,
                "medication_id": medication.medication_id,
                "prescribed_at": prescribed_at,
                "indication": medication.indication,
            },
        )

    def add_document(self, document: Document) -> None:
        self._exec(
            """
            MERGE (d:Document {document_id: $document_id})
            SET d.doc_type = $doc_type,
                d.title = $title,
                d.extracted_at = $extracted_at
            """,
            {
                "document_id": document.document_id,
                "doc_type": document.doc_type.value,
                "title": document.title,
                "extracted_at": document.extracted_at,
            },
        )
        if document.encounter_id:
            self._exec(
                """
                MATCH (e:Encounter {encounter_id: $encounter_id})
                MATCH (d:Document {document_id: $document_id})
                MERGE (e)-[:HAS_DOCUMENT]->(d)
                """,
                {"encounter_id": document.encounter_id, "document_id": document.document_id},
            )
        else:
            self._exec(
                """
                MATCH (p:Patient {patient_id: $patient_id})
                MATCH (d:Document {document_id: $document_id})
                MERGE (p)-[:HAS_DOCUMENT_DIRECT]->(d)
                """,
                {"patient_id": document.patient_id, "document_id": document.document_id},
            )

    def get_active_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch(
            """
            MATCH (p:Patient {patient_id: $patient_id})-[:TAKES_MEDICATION]->(m:Medication)
            WHERE m.status = $status
            RETURN m.medication_id AS medication_id,
                   m.name AS name,
                   m.indication AS indication,
                   m.prescriber AS prescriber,
                   m.status AS status,
                   m.start_date AS start_date,
                   m.end_date AS end_date
            """,
            {"patient_id": patient_id, "status": "active"},
        )

    def get_encounter_record(self, encounter_id: str) -> Dict[str, Any]:
        encounter_rows = self._fetch(
            """
            MATCH (e:Encounter {encounter_id: $encounter_id})
            RETURN e.encounter_id AS encounter_id,
                   e.encounter_type AS encounter_type,
                   e.start_time AS start_time,
                   e.end_time AS end_time
            """,
            {"encounter_id": encounter_id},
        )
        observations = self._fetch(
            """
            MATCH (e:Encounter {encounter_id: $encounter_id})-[:HAS_OBSERVATION]->(o:Observation)
            RETURN o.observation_id AS observation_id,
                   o.category AS category,
                   o.name AS name,
                   o.value AS value,
                   o.value_numeric AS value_numeric,
                   o.unit AS unit,
                   o.observed_at AS observed_at
            """,
            {"encounter_id": encounter_id},
        )
        medications = self._fetch(
            """
            MATCH (e:Encounter {encounter_id: $encounter_id})-[:HAS_MEDICATION]->(m:Medication)
            RETURN m.medication_id AS medication_id,
                   m.name AS name,
                   m.indication AS indication,
                   m.prescriber AS prescriber,
                   m.status AS status,
                   m.start_date AS start_date,
                   m.end_date AS end_date
            """,
            {"encounter_id": encounter_id},
        )
        documents = self._fetch(
            """
            MATCH (e:Encounter {encounter_id: $encounter_id})-[:HAS_DOCUMENT]->(d:Document)
            RETURN d.document_id AS document_id,
                   d.doc_type AS doc_type,
                   d.title AS title,
                   d.extracted_at AS extracted_at
            """,
            {"encounter_id": encounter_id},
        )
        return {
            "encounter": encounter_rows[0] if encounter_rows else None,
            "observations": observations,
            "medications": medications,
            "documents": documents,
        }

    def get_patient_timeline(self, patient_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        return self._fetch(
            """
            MATCH (p:Patient {patient_id: $patient_id})-[:HAS_ENCOUNTER]->(e:Encounter)
            RETURN 'encounter' AS event_type,
                   e.encounter_id AS ref_id,
                   e.start_time AS event_time
            UNION ALL
            MATCH (p:Patient {patient_id: $patient_id})-[:TAKES_MEDICATION]->(m:Medication)
            RETURN 'medication' AS event_type,
                   m.medication_id AS ref_id,
                   m.start_date AS event_time
            UNION ALL
            MATCH (p:Patient {patient_id: $patient_id})-[:HAS_DOCUMENT_DIRECT]->(d:Document)
            RETURN 'document' AS event_type,
                   d.document_id AS ref_id,
                   d.extracted_at AS event_time
            ORDER BY event_time DESC
            LIMIT $limit
            """,
            {"patient_id": patient_id, "limit": limit},
        )

    def get_medication_pairs(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch(
            """
            MATCH (p:Patient {patient_id: $patient_id})-[:TAKES_MEDICATION]->(m1:Medication)
            MATCH (p)-[:TAKES_MEDICATION]->(m2:Medication)
            WHERE m1.medication_id < m2.medication_id
            RETURN m1.medication_id AS medication_a_id,
                   m1.name AS medication_a_name,
                   m2.medication_id AS medication_b_id,
                   m2.name AS medication_b_name
            """,
            {"patient_id": patient_id},
        )


class Neo4jGraphStore(GraphStore):
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        database: Optional[str],
        max_pool_size: int,
        acquire_timeout: int,
    ) -> None:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError("neo4j is not installed. Run `pip install neo4j`.") from exc

        self._driver = GraphDatabase.driver(
            url,
            auth=(username, password),
            max_connection_pool_size=max_pool_size,
            connection_acquisition_timeout=acquire_timeout,
        )
        self._database = database
        self._init_schema()

    def _execute(self, query: str, params: Optional[dict] = None) -> None:
        with self._driver.session(database=self._database) as session:
            session.run(query, params or {})

    def _fetch(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        with self._driver.session(database=self._database) as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    def _init_schema(self) -> None:
        self._execute("CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.patient_id IS UNIQUE")
        self._execute("CREATE CONSTRAINT encounter_id IF NOT EXISTS FOR (e:Encounter) REQUIRE e.encounter_id IS UNIQUE")
        self._execute("CREATE CONSTRAINT observation_id IF NOT EXISTS FOR (o:Observation) REQUIRE o.observation_id IS UNIQUE")
        self._execute("CREATE CONSTRAINT medication_id IF NOT EXISTS FOR (m:Medication) REQUIRE m.medication_id IS UNIQUE")
        self._execute("CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE")

    def close(self) -> None:
        self._driver.close()

    def add_patient(self, profile: PatientProfile) -> None:
        self._execute(
            """
            MERGE (p:Patient {patient_id: $patient_id})
            SET p.name = $name,
                p.date_of_birth = $date_of_birth,
                p.sex = $sex
            """,
            {
                "patient_id": profile.patient_id,
                "name": profile.name,
                "date_of_birth": profile.date_of_birth,
                "sex": profile.sex,
            },
        )

    def add_encounter(self, encounter: Encounter) -> None:
        created_at = encounter.metadata.created_at or encounter.start_time
        self._execute(
            """
            MERGE (e:Encounter {encounter_id: $encounter_id})
            SET e.encounter_type = $encounter_type,
                e.start_time = $start_time,
                e.end_time = $end_time
            """,
            {
                "encounter_id": encounter.encounter_id,
                "encounter_type": encounter.encounter_type,
                "start_time": encounter.start_time,
                "end_time": encounter.end_time,
            },
        )
        self._execute(
            """
            MATCH (p:Patient {patient_id: $patient_id})
            MATCH (e:Encounter {encounter_id: $encounter_id})
            MERGE (p)-[r:HAS_ENCOUNTER]->(e)
            SET r.created_at = $created_at
            """,
            {
                "patient_id": encounter.patient_id,
                "encounter_id": encounter.encounter_id,
                "created_at": created_at,
            },
        )

    def add_observation(self, observation: Observation) -> None:
        self._execute(
            """
            MERGE (o:Observation {observation_id: $observation_id})
            SET o.category = $category,
                o.name = $name,
                o.value = $value,
                o.value_numeric = $value_numeric,
                o.unit = $unit,
                o.observed_at = $observed_at
            """,
            {
                "observation_id": observation.observation_id,
                "category": observation.category.value,
                "name": observation.name,
                "value": observation.value,
                "value_numeric": observation.value_numeric,
                "unit": observation.unit,
                "observed_at": observation.observed_at,
            },
        )
        if observation.encounter_id:
            self._execute(
                """
                MATCH (e:Encounter {encounter_id: $encounter_id})
                MATCH (o:Observation {observation_id: $observation_id})
                MERGE (e)-[:HAS_OBSERVATION]->(o)
                """,
                {"encounter_id": observation.encounter_id, "observation_id": observation.observation_id},
            )

    def add_medication(self, medication: Medication) -> None:
        self._execute(
            """
            MERGE (m:Medication {medication_id: $medication_id})
            SET m.name = $name,
                m.indication = $indication,
                m.prescriber = $prescriber,
                m.status = $status,
                m.start_date = $start_date,
                m.end_date = $end_date
            """,
            {
                "medication_id": medication.medication_id,
                "name": medication.name,
                "indication": medication.indication,
                "prescriber": medication.prescriber,
                "status": medication.status.value,
                "start_date": medication.start_date,
                "end_date": medication.end_date,
            },
        )
        if medication.encounter_id:
            self._execute(
                """
                MATCH (e:Encounter {encounter_id: $encounter_id})
                MATCH (m:Medication {medication_id: $medication_id})
                MERGE (e)-[:HAS_MEDICATION]->(m)
                """,
                {"encounter_id": medication.encounter_id, "medication_id": medication.medication_id},
            )
        prescribed_at = medication.start_date or medication.metadata.created_at
        self._execute(
            """
            MATCH (p:Patient {patient_id: $patient_id})
            MATCH (m:Medication {medication_id: $medication_id})
            MERGE (p)-[r:TAKES_MEDICATION]->(m)
            SET r.prescribed_at = $prescribed_at,
                r.indication = $indication
            """,
            {
                "patient_id": medication.patient_id,
                "medication_id": medication.medication_id,
                "prescribed_at": prescribed_at,
                "indication": medication.indication,
            },
        )

    def add_document(self, document: Document) -> None:
        self._execute(
            """
            MERGE (d:Document {document_id: $document_id})
            SET d.doc_type = $doc_type,
                d.title = $title,
                d.extracted_at = $extracted_at
            """,
            {
                "document_id": document.document_id,
                "doc_type": document.doc_type.value,
                "title": document.title,
                "extracted_at": document.extracted_at,
            },
        )
        if document.encounter_id:
            self._execute(
                """
                MATCH (e:Encounter {encounter_id: $encounter_id})
                MATCH (d:Document {document_id: $document_id})
                MERGE (e)-[:HAS_DOCUMENT]->(d)
                """,
                {"encounter_id": document.encounter_id, "document_id": document.document_id},
            )
        else:
            self._execute(
                """
                MATCH (p:Patient {patient_id: $patient_id})
                MATCH (d:Document {document_id: $document_id})
                MERGE (p)-[:HAS_DOCUMENT_DIRECT]->(d)
                """,
                {"patient_id": document.patient_id, "document_id": document.document_id},
            )

    def get_active_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch(
            """
            MATCH (p:Patient {patient_id: $patient_id})-[:TAKES_MEDICATION]->(m:Medication)
            WHERE m.status = $status
            RETURN m.medication_id AS medication_id,
                   m.name AS name,
                   m.indication AS indication,
                   m.prescriber AS prescriber,
                   m.status AS status,
                   m.start_date AS start_date,
                   m.end_date AS end_date
            """,
            {"patient_id": patient_id, "status": "active"},
        )

    def get_encounter_record(self, encounter_id: str) -> Dict[str, Any]:
        encounter_rows = self._fetch(
            """
            MATCH (e:Encounter {encounter_id: $encounter_id})
            RETURN e.encounter_id AS encounter_id,
                   e.encounter_type AS encounter_type,
                   e.start_time AS start_time,
                   e.end_time AS end_time
            """,
            {"encounter_id": encounter_id},
        )
        observations = self._fetch(
            """
            MATCH (e:Encounter {encounter_id: $encounter_id})-[:HAS_OBSERVATION]->(o:Observation)
            RETURN o.observation_id AS observation_id,
                   o.category AS category,
                   o.name AS name,
                   o.value AS value,
                   o.value_numeric AS value_numeric,
                   o.unit AS unit,
                   o.observed_at AS observed_at
            """,
            {"encounter_id": encounter_id},
        )
        medications = self._fetch(
            """
            MATCH (e:Encounter {encounter_id: $encounter_id})-[:HAS_MEDICATION]->(m:Medication)
            RETURN m.medication_id AS medication_id,
                   m.name AS name,
                   m.indication AS indication,
                   m.prescriber AS prescriber,
                   m.status AS status,
                   m.start_date AS start_date,
                   m.end_date AS end_date
            """,
            {"encounter_id": encounter_id},
        )
        documents = self._fetch(
            """
            MATCH (e:Encounter {encounter_id: $encounter_id})-[:HAS_DOCUMENT]->(d:Document)
            RETURN d.document_id AS document_id,
                   d.doc_type AS doc_type,
                   d.title AS title,
                   d.extracted_at AS extracted_at
            """,
            {"encounter_id": encounter_id},
        )
        return {
            "encounter": encounter_rows[0] if encounter_rows else None,
            "observations": observations,
            "medications": medications,
            "documents": documents,
        }

    def get_patient_timeline(self, patient_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        return self._fetch(
            """
            MATCH (p:Patient {patient_id: $patient_id})-[:HAS_ENCOUNTER]->(e:Encounter)
            RETURN 'encounter' AS event_type,
                   e.encounter_id AS ref_id,
                   e.start_time AS event_time
            UNION ALL
            MATCH (p:Patient {patient_id: $patient_id})-[:TAKES_MEDICATION]->(m:Medication)
            RETURN 'medication' AS event_type,
                   m.medication_id AS ref_id,
                   m.start_date AS event_time
            UNION ALL
            MATCH (p:Patient {patient_id: $patient_id})-[:HAS_DOCUMENT_DIRECT]->(d:Document)
            RETURN 'document' AS event_type,
                   d.document_id AS ref_id,
                   d.extracted_at AS event_time
            ORDER BY event_time DESC
            LIMIT $limit
            """,
            {"patient_id": patient_id, "limit": limit},
        )

    def get_medication_pairs(self, patient_id: str) -> List[Dict[str, Any]]:
        return self._fetch(
            """
            MATCH (p:Patient {patient_id: $patient_id})-[:TAKES_MEDICATION]->(m1:Medication)
            MATCH (p)-[:TAKES_MEDICATION]->(m2:Medication)
            WHERE m1.medication_id < m2.medication_id
            RETURN m1.medication_id AS medication_a_id,
                   m1.name AS medication_a_name,
                   m2.medication_id AS medication_b_id,
                   m2.name AS medication_b_name
            """,
            {"patient_id": patient_id},
        )


def get_graph_store() -> Optional[GraphStore]:
    config = load_graph_config()
    if not config.enabled:
        return None
    if config.provider == "kuzu":
        return KuzuGraphStore(config.kuzu_path)
    if config.provider == "neo4j":
        if not config.neo4j_url or not config.neo4j_username or not config.neo4j_password:
            raise RuntimeError("Missing Neo4j settings for graph store.")
        return Neo4jGraphStore(
            config.neo4j_url,
            config.neo4j_username,
            config.neo4j_password,
            config.neo4j_database,
            config.neo4j_max_pool,
            config.neo4j_acquire_timeout,
        )
    raise RuntimeError(f"Unsupported graph provider: {config.provider}")
