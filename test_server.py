import unittest
import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import server


def airtable_record(record_id, mapping_name, values):
    mapping = server.FIELDS[mapping_name]
    return {
        "id": record_id,
        "fields": {mapping[field]: value for field, value in values.items()},
    }


class ProjectsReadModelTests(unittest.TestCase):
    def test_active_mission_decision_joins_project_by_record_id(self):
        state = airtable_record("rec-state", "learning_state", {
            "mission": "MISSION-1",
            "confidence": 72,
            "subject": "AI Engineering",
        })
        mission = airtable_record("rec-mission", "missions", {
            "id": "MISSION-1",
            "name": "Build a retrieval service",
        })
        project = airtable_record("rec-project", "projects", {
            "name": "RAG service",
            "stage": 2,
            "status": {"name": "In Progress"},
            "architecture_complete": True,
            "code_complete": False,
            "interview_ready": False,
        })
        decision = airtable_record("rec-decision", "project_decisions", {
            "project": "RAG service",
            "project_record_id": "rec-project",
            "mission": "MISSION-1",
            "goal": "Practice retrieval design",
            "action": {"name": "Build increment"},
            "mutation": "None",
        })
        other_decision = airtable_record("rec-old", "project_decisions", {
            "project": "Other project",
            "project_record_id": "rec-other",
            "mission": "MISSION-OLD",
        })

        def records(table_id, **_kwargs):
            return {
                server.TABLES["learning_state"]: [state],
                server.TABLES["missions"]: [mission],
                server.TABLES["projects"]: [project],
                server.TABLES["project_decisions"]: [decision, other_decision],
                server.TABLES["radar"]: [],
            }[table_id]

        with patch.object(server.AirtableClient, "list_records", side_effect=records):
            result = server.live_state(server.AirtableClient("test-token"))

        self.assertEqual(result["state"]["confidence"], 72)
        self.assertNotIn("mastery", result["state"])
        self.assertEqual(len(result["project_decisions"]), 1)
        self.assertEqual(result["project_decisions"][0]["project_record"]["record_id"], "rec-project")
        self.assertEqual(result["project_decisions"][0]["action"], "Build increment")
        self.assertTrue(result["projects"][0]["architecture_complete"])
        self.assertFalse(result["projects"][0]["code_complete"])

    def test_legacy_name_join_only_resolves_unique_project(self):
        projects = [
            airtable_record("rec-one", "projects", {"name": "Same name"}),
            airtable_record("rec-two", "projects", {"name": "Same name"}),
        ]
        decision = airtable_record("rec-decision", "project_decisions", {
            "project": "Same name",
            "mission": "MISSION-1",
        })

        def records(table_id, **_kwargs):
            return {
                server.TABLES["learning_state"]: [airtable_record("rec-state", "learning_state", {"mission": "MISSION-1"})],
                server.TABLES["missions"]: [],
                server.TABLES["projects"]: projects,
                server.TABLES["project_decisions"]: [decision],
                server.TABLES["radar"]: [],
            }[table_id]

        with patch.object(server.AirtableClient, "list_records", side_effect=records):
            result = server.live_state(server.AirtableClient("test-token"))

        self.assertIsNone(result["project_decisions"][0]["project_record"])


class AirtableClientTests(unittest.TestCase):
    @patch("server.urlopen")
    def test_list_records_requests_field_id_keyed_response(self, mock_urlopen):
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps({
            "records": [{"id": "rec-project", "fields": {"fld-project-name": "RAG service"}}]
        }).encode("utf-8")

        records = server.AirtableClient("test-token", "app-test").list_records("tbl-projects")

        request = mock_urlopen.call_args.args[0]
        query = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(query["returnFieldsByFieldId"], ["true"])
        self.assertEqual(records[0]["fields"]["fld-project-name"], "RAG service")


if __name__ == "__main__":
    unittest.main()
