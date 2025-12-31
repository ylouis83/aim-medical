import unittest
from datetime import datetime

from bootstrap import add_src_path

add_src_path()

from jkmem.medical.report_parser import ReportParser
from jkmem.models import DocumentType, ObservationCategory


class TestReportParser(unittest.TestCase):
    def test_parse_report(self) -> None:
        parser = ReportParser()
        report_text = """Hemoglobin: 12.3 g/dL
Glucose: 105 mg/dL
Note: Normal"""
        extracted_at = datetime(2024, 1, 1, 8, 0, 0)

        document, observations = parser.parse(
            report_text=report_text,
            patient_id="patient_1",
            encounter_id="enc_1",
            document_id="doc_1",
            doc_type=DocumentType.LAB,
            extracted_at=extracted_at,
        )

        self.assertEqual(document.document_id, "doc_1")
        self.assertEqual(document.doc_type, DocumentType.LAB)
        self.assertEqual(len(observations), 3)
        self.assertTrue(all(obs.category == ObservationCategory.LAB for obs in observations))
        self.assertEqual(observations[0].name, "Hemoglobin")
        self.assertEqual(observations[0].value, "12.3")
        self.assertEqual(observations[0].unit, "g/dL")
        self.assertEqual(observations[0].value_numeric, 12.3)


if __name__ == "__main__":
    unittest.main()
