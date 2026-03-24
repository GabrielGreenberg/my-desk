"""Vercel serverless function: Notion task CRUD proxy."""

import json, os
from http.server import BaseHTTPRequestHandler
import urllib.request

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
DATABASE_ID = "9b491202-7c21-4a10-b03f-788c1cd82277"
NOTION_VERSION = "2022-06-28"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def notion_request(method, url, body=None):
    """Make a request to the Notion API."""
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def list_tasks():
    """Query the database for active (non-completed) tasks."""
    body = {
        "filter": {
            "or": [
                {"property": "Status", "status": {"equals": "Not started"}},
                {"property": "Status", "status": {"equals": "In progress"}},
                {"property": "Status", "status": {"equals": "To Do"}},
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
        # Extract title
        title_prop = props.get("Task name", props.get("Task", props.get("Name", {})))
        title = ""
        if title_prop.get("title"):
            title = "".join(t.get("plain_text", "") for t in title_prop["title"])

        # Extract status
        status = ""
        if props.get("Status", {}).get("status"):
            status = props["Status"]["status"].get("name", "")

        # Extract due date
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
    """Create a new task in the database."""
    properties = {
        "Task name": {"title": [{"text": {"content": title}}]},
        "Status": {"status": {"name": "To Do"}},
    }
    if due:
        properties["Due"] = {"date": {"start": due}}

    body = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties,
    }
    result = notion_request("POST", "https://api.notion.com/v1/pages", body)
    return {"id": result["id"], "title": title, "status": "To Do", "due": due}


def update_task(page_id, updates):
    """Update a task's properties."""
    properties = {}
    if "title" in updates:
        properties["Task name"] = {"title": [{"text": {"content": updates["title"]}}]}
    if "status" in updates:
        properties["Status"] = {"status": {"name": updates["status"]}}
    if "due" in updates:
        properties["Due"] = {"date": {"start": updates["due"]} if updates["due"] else None}

    body = {"properties": properties}
    notion_request("PATCH", f"https://api.notion.com/v1/pages/{page_id}", body)
    return {"ok": True}


def archive_task(page_id):
    """Archive (soft-delete) a task."""
    body = {"archived": True}
    notion_request("PATCH", f"https://api.notion.com/v1/pages/{page_id}", body)
    return {"ok": True}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GET /api/notion → list tasks"""
        try:
            tasks = list_tasks()
            self._send_json({"tasks": tasks})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        """POST /api/notion → create or update task"""
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
