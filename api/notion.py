"""Vercel serverless function: Notion task CRUD proxy."""

import json, os
from http.server import BaseHTTPRequestHandler
import urllib.request

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
DATABASE_ID = "24d95563-22a9-484f-9db0-e93d9bbca600"
NOTION_VERSION = "2022-06-28"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def notion_request(method, url, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def list_tasks():
    body = {
        "filter": {
            "or": [
                {"property": "Done", "status": {"equals": "Not started"}},
                {"property": "Done", "status": {"equals": "In progress"}},
            ]
        },
        "sorts": [
            {"property": "Due", "direction": "ascending"},
            {"timestamp": "created_time", "direction": "descending"}
        ],
        "page_size": 50
    }
    result = notion_request("POST", f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", body)
    tasks = []
    for page in result.get("results", []):
        props = page["properties"]
        # Title from "Task" property
        title_prop = props.get("Task", {})
        title = ""
        if title_prop.get("title"):
            title = "".join(t.get("plain_text", "") for t in title_prop["title"])

        # Status from "Done" property
        status = ""
        if props.get("Done", {}).get("status"):
            status = props["Done"]["status"].get("name", "")

        # Due date
        due = None
        if props.get("Due", {}).get("date"):
            due = props["Due"]["date"].get("start")

        tasks.append({
            "id": page["id"],
            "title": title,
            "status": status,
            "due": due,
            "url": page.get("url", ""),
        })
    return tasks


def create_task(title, due=None):
    properties = {
        "Task": {"title": [{"text": {"content": title}}]},
        "Done": {"status": {"name": "Not started"}},
    }
    if due:
        properties["Due"] = {"date": {"start": due}}
    body = {"parent": {"database_id": DATABASE_ID}, "properties": properties}
    result = notion_request("POST", "https://api.notion.com/v1/pages", body)
    return {"id": result["id"], "title": title, "status": "Not started", "due": due}


def update_task(page_id, updates):
    properties = {}
    if "title" in updates:
        properties["Task"] = {"title": [{"text": {"content": updates["title"]}}]}
    if "status" in updates:
        properties["Done"] = {"status": {"name": updates["status"]}}
    if "due" in updates:
        properties["Due"] = {"date": {"start": updates["due"]} if updates["due"] else None}
    notion_request("PATCH", f"https://api.notion.com/v1/pages/{page_id}", {"properties": properties})
    return {"ok": True}


def archive_task(page_id):
    notion_request("PATCH", f"https://api.notion.com/v1/pages/{page_id}", {"archived": True})
    return {"ok": True}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            tasks = list_tasks()
            self._send_json({"tasks": tasks})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
            action = body.get("action", "create")

            if action == "create":
                result = create_task(body.get("title", ""), body.get("due"))
                self._send_json(result)
            elif action == "update":
                result = update_task(body["id"], body.get("updates", {}))
                self._send_json(result)
            elif action == "archive":
                result = archive_task(body["id"])
                self._send_json(result)
            elif action == "complete":
                result = update_task(body["id"], {"status": "Done"})
                self._send_json(result)
            else:
                self._send_json({"error": f"Unknown action: {action}"}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
