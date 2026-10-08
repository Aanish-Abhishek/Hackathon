import unittest
from types import SimpleNamespace
from unittest.mock import patch
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.main import app
from app.models.response import AnalysisResponse, Finding
from app.services.analyzer import (
    LogValidationError,
    MissingRepositoryError,
    inspect_repository,
    analyze_logs,
    parse_uploaded_logs,
)


class ParseUploadedLogsTests(unittest.TestCase):
    def test_parses_utf8_log_and_extracts_error_types(self):
        logs = parse_uploaded_logs([
            ("incident.log", b"TimeoutError: operation timed out\nValueError: bad input")
        ])

        self.assertEqual(logs[0].filename, "incident.log")
        self.assertEqual(logs[0].error_types, ("TimeoutError", "ValueError"))

    def test_rejects_unsupported_extension(self):
        with self.assertRaises(LogValidationError):
            parse_uploaded_logs([("incident.json", b"{}")])

    def test_rejects_invalid_utf8(self):
        with self.assertRaises(LogValidationError):
            parse_uploaded_logs([("incident.log", b"\xff")])

    def test_rejects_empty_logs(self):
        with self.assertRaises(LogValidationError):
            parse_uploaded_logs([("incident.log", b" \n")])


class InspectRepositoryTests(unittest.TestCase):
    def test_loads_required_python_source(self):
        source = inspect_repository()

        self.assertIn("app.py", source)
        self.assertIn("utils.py", source)
        self.assertIn("process_batch", source["app.py"])

    def test_reports_missing_required_source_files(self):
        with TemporaryDirectory() as temporary_directory:
            Path(temporary_directory, "app.py").write_text(
                "def run(): pass\n",
                encoding="utf-8",
            )
            with self.assertRaises(MissingRepositoryError):
                inspect_repository(Path(temporary_directory))


class GptAnalysisTests(unittest.TestCase):
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("app.services.analyzer.OpenAI")
    def test_submits_log_and_repository_to_gpt(self, openai_client):
        openai_client.return_value.chat.completions.create.return_value = (
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"summary":"Timeout in batch processing.",'
                                '"findings":[{"error_type":"TimeoutError",'
                                '"suspected_root_cause":"The connection may remain open.",'
                                '"file":"app.py","function":"process_batch",'
                                '"suggested_fix":"Close the connection on every path.",'
                                '"severity":"High","confidence":0.9,'
                                '"evidence":["TimeoutError in sample.log"]}]}'
                            )
                        )
                    )
                ]
            )
        )
        logs = parse_uploaded_logs([
            ("sample.log", b"TimeoutError: database connection timed out")
        ])

        result = analyze_logs(logs)

        self.assertEqual(result.analysis_mode, "gpt")
        self.assertEqual(result.findings[0].function, "process_batch")
        call = openai_client.return_value.chat.completions.create.call_args
        prompt = call.kwargs["messages"][1]["content"]
        self.assertIn("database connection timed out", prompt)
        self.assertIn("def process_batch", prompt)
        self.assertEqual(call.kwargs["model"], "gpt-4o-mini")


class AnalyzeLogsApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_rejects_unsupported_file_type(self):
        response = self.client.post(
            "/analyze-logs",
            files={"files": ("incident.json", b"{}", "application/json")},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn(".log and .txt", response.json()["detail"])

    @patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_reports_missing_gpt_configuration(self):
        response = self.client.post(
            "/analyze-logs",
            files={"files": ("incident.log", b"TimeoutError", "text/plain")},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENAI_API_KEY", response.json()["detail"])

    @patch("app.routes.logs.run_analysis")
    def test_returns_structured_findings_and_context(self, run_analysis):
        run_analysis.return_value = AnalysisResponse(
            summary="Connection timeout points to a resource leak.",
            analyzed_files=["incident.log"],
            findings=[
                Finding(
                    error_type="TimeoutError",
                    suspected_root_cause="Connections are not consistently closed.",
                    file="app.py",
                    function="process_batch",
                    suggested_fix="Close the connection in a finally block.",
                    severity="High",
                    confidence=0.91,
                    evidence=["TimeoutError in sample.log", "app.py:process_batch"],
                )
            ],
        )

        response = self.client.post(
            "/analyze-logs",
            files={"files": ("incident.log", b"TimeoutError: timed out", "text/plain")},
            data={
                "application_name": "TraceFix",
                "environment_name": "Production",
                "incident_details": "Batch processing failed",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["findings"][0]["file"], "app.py")
        self.assertEqual(response.json()["analyzed_files"], ["incident.log"])
        self.assertEqual(
            run_analysis.call_args.kwargs["incident_context"],
            {
                "application_name": "TraceFix",
                "environment_name": "Production",
                "incident_details": "Batch processing failed",
            },
        )


if __name__ == "__main__":
    unittest.main()
