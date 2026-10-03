from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "appPgdJLtBMlQluhK")
PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "0.0.0.0")
ROOT = Path(__file__).resolve().parent

TABLES = {
    "learning_state": "tbl12yjcLHZb8DX1H",
    "missions": "tblZhKOfRec46ejjO",
    "projects": "tblW9Gn7cRLkYU6d4",
    "project_decisions": "tblBiSytzZ4UUE7pA",
    "radar": "tblDoUHNT7PgWT1EM",
}

FIELDS = {
    "learning_state": {
        "id": "fldiY7MFSKV01j01w",
        "subject": "fldxq2ex3lz3lca42",
        "topic": "fldw7i1ZxlMr6eiXP",
        "mission": "fldxnGkArtbR3gtLq",
        # Airtable's learner-state field is Confidence, not assessed mastery.
        "confidence": "fldwCHbEMCIUTu0LP",
        "understanding": "fldoqhoRwhrnIAtij",
        "weakness": "fldQD7eeuaQ80iwaB",
        "mode": "fldP2rJRz1v2JElbm",
        "energy": "fldCgdhwHXQ0gG4na",
        "time": "fldIkFOWYdlhG2DVM",
        "checkpoint": "fldJVcbe1mvjvX0ZR",
    },
    "missions": {
        "id": "fldgX0yQ8PvD8howS",
        "name": "fldT3Gkt7OxeO6ksr",
        "topic": "fldB9fH0ZMBLWC8Pi",
        "subject": "fldY18Q9neQ6DLoxT",
        "goal": "fldCHX2dUMPhzUcrH",
        "skills": "fldJuIiJ8KsG6YkOW",
        "mode": "fldWjsARW7Ee8qA5q",
        "difficulty": "fldhZWwPLLn5ObAzX",
        "status": "fldVU4avumWg3SIcC",
        "engine_state": "fldYEhuPJWYb9M9xl",
        "checkpoint": "fldryQBfozLpZln95",
    },
    "projects": {
        "name": "fldBEmdjCAFVsk3vI",
        "stage": "fldgN1oomPcZd4wya",
        "goal": "fldUtoDiAJ67YEwwX",
        "skills": "fldJKqDU9QDqRAisM",
        "status": "fldIMt1T2BO8a2GVu",
        "architecture_complete": "fld3U7pIKWtWb6RP5",
        "code_complete": "fld4vFjs4LIJDLUKb",
        "tests_complete": "fldNSOQCge9SeFg6E",
        "deployed": "fldKwQqg4fceTKkkD",
        "observed": "fldOAOItyiCBmlqb5",
        "business_impact": "fld4J0oxaiGIaRwre",
        "resume_bullet": "fld3UMjD9MVePun8Q",
        "interview_ready": "fld5tlq174Gjggcc5",
        "notes": "fldnaRJtUWyBU0sdW",
    },
    "project_decisions": {
        "id": "fldMd3dofWnUuT5TI",
        "project": "fldotVXFUdBeubVVF",
        "project_record_id": "fldV0mtWyZHmiWPNC",
        "mission": "fldlex8NovABvXkjC",
        "subject": "fldMKimDYJjkT6qU5",
        "goal": "fldXpfsiZqIxHIwsg",
        "mastery": "fldAoteUUL7fitXmi",
        "weakness": "fldbSpBou0l0eQmTD",
        "action": "fldZSyQF5O8gwA5DI",
        "reason": "fldphLHZJWaArfgKl",
        "status": "fldd893Sjo4MN9tDz",
        "mutation": "fldK11xZ14b3H8Wkz",
    },
    "radar": {
        "technology": "fldThPlnQQa6w9JFw",
        "category": "fldbMmwa9WCieccF3",
        "status": "fld8uatlLBUmQRpKU",
        "relevance": "fld8wecSwB9Z4o6Mk",
        "maturity": "fldx0AUdCkxxCXatw",
        "career": "fldYRrC7ApMf5b1VR",
        "learning": "fldscx10juejzmstI",
        "decision": "fld7gs9vqd6y88lEu",
    },
}


def choice(value: Any) -> Any:
    if isinstance(value, dict) and "name" in value:
        return value["name"]
    return value


class AirtableError(RuntimeError):
    pass


class AirtableClient:
    def __init__(self, token: str, base_id: str = BASE_ID):
        self.token = token
        self.base_id = base_id

    def list_records(self, table_id: str, page_size: int = 100, max_pages: int = 10) -> list[dict[str, Any]]:
        if not self.token:
            raise AirtableError("AIRTABLE_TOKEN is not configured")
        records: list[dict[str, Any]] = []
        offset = None
        for _ in range(max_pages):
            url = f"https://api.airtable.com/v0/{self.base_id}/{quote(table_id, safe='')}?pageSize={page_size}"
            if offset:
                url += f"&offset={quote(offset, safe='')}"
            req = Request(url, headers={"Authorization": f"Bearer {self.token}"})
            try:
                with urlopen(req, timeout=15) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            except (HTTPError, URLError, TimeoutError) as exc:
                raise AirtableError(f"Airtable request failed: {exc}") from exc
            records.extend(payload.get("records", []))
            offset = payload.get("offset")
            if not offset:
                break
        return records


def fields_of(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("fields", {})


def normalized_record(record: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    src = fields_of(record)
    return {
        "record_id": record.get("id"),
        **{name: choice(src.get(field_id)) for name, field_id in mapping.items()},
    }


def live_state(client: AirtableClient) -> dict[str, Any]:
    state_records = client.list_records(TABLES["learning_state"], page_size=10)
    missions = client.list_records(TABLES["missions"], page_size=50)
    projects = client.list_records(TABLES["projects"], page_size=50)
    decisions = client.list_records(TABLES["project_decisions"], page_size=50)
    radar = client.list_records(TABLES["radar"], page_size=50)

    state = normalized_record(state_records[0], FIELDS["learning_state"]) if state_records else {}
    current_mission = next((
        normalized_record(r, FIELDS["missions"])
        for r in missions
        if choice(fields_of(r).get(FIELDS["missions"]["id"])) == state.get("mission")
    ), None)

    project_rows = [normalized_record(r, FIELDS["projects"]) for r in projects]
    projects_by_record_id = {project["record_id"]: project for project in project_rows}
    projects_by_name: dict[str, list[dict[str, Any]]] = {}
    for project in project_rows:
        if project.get("name"):
            projects_by_name.setdefault(str(project["name"]).strip().casefold(), []).append(project)

    # Keep every decision for the active mission. The table has no timestamp field,
    # so ordering records here would incorrectly imply which decision is newest.
    active_mission_id = state.get("mission")
    current_decisions = [normalized_record(r, FIELDS["project_decisions"]) for r in decisions]
    current_decisions = [d for d in current_decisions if active_mission_id and d.get("mission") == active_mission_id]
    for decision in current_decisions:
        project = projects_by_record_id.get(decision.get("project_record_id"))
        if project is None and decision.get("project"):
            # Legacy decisions may lack the record ID. Resolve only an unambiguous name.
            matches = projects_by_name.get(str(decision["project"]).strip().casefold(), [])
            if len(matches) == 1:
                project = matches[0]
        decision["project_record"] = project

    radar_rows = [normalized_record(r, FIELDS["radar"]) for r in radar]
    return {
        "connected": True,
        "source": "Airtable",
        "state": state,
        "mission": current_mission,
        "projects": project_rows,
        "project_decisions": current_decisions,
        "radar": radar_rows,
    }


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    server_version = "LearningOS/0.2"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[LearningOS] {fmt % args}")

    def do_GET(self) -> None:
        if self.path == "/api/health":
            json_response(self, 200, {"ok": True, "airtable_configured": bool(os.environ.get("AIRTABLE_TOKEN"))})
            return
        if self.path == "/api/state":
            token = os.environ.get("AIRTABLE_TOKEN", "")
            if not token:
                json_response(self, 503, {
                    "ok": False,
                    "error": "AIRTABLE_TOKEN is not configured. The UI is running, but live state is unavailable.",
                })
                return
            try:
                json_response(self, 200, live_state(AirtableClient(token)))
            except AirtableError as exc:
                json_response(self, 502, {"ok": False, "error": str(exc)})
            return

        rel = self.path.lstrip("/") or "index.html"
        file_path = (ROOT / rel).resolve()
        if ROOT not in file_path.parents and file_path != ROOT:
            json_response(self, 404, {"ok": False, "error": "Not found"})
            return
        if file_path.is_file():
            content_type = "text/html; charset=utf-8" if file_path.suffix == ".html" else "text/plain; charset=utf-8"
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        json_response(self, 404, {"ok": False, "error": "Not found"})


if __name__ == "__main__":
    print(f"Learning OS UI: http://127.0.0.1:{PORT}")
    print(f"Network access: http://<computer-ip>:{PORT}")
    print("Live Airtable: " + ("configured" if os.environ.get("AIRTABLE_TOKEN") else "NOT configured"))
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
