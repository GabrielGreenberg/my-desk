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
            "and": [
                {"property": "Done", "status": {"does_not_equal": "Done"}},
                {
                    "property": "Status",
                    "multi_select": {"does_not_contain": "Completed"}
                },
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
            "doneStatus": status,
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


def complete_task(page_id):
    """Mark a task as Completed (sets Status multi-select to Completed)."""
    properties = {
        "Status": {"multi_select": [{"name": "Completed"}]},
    }
    notion_request("PATCH", f"https://api.notion.com/v1/pages/{page_id}", {"properties": properties})
    return {"ok": True}


def _rich_text_html(rich_text_arr):
    """Convert Notion rich_text array to HTML."""
    parts = []
    for rt in rich_text_arr:
        text = rt.get("plain_text", "")
        if not text:
            continue
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ann = rt.get("annotations", {})
        if ann.get("code"):
            text = f"<code>{text}</code>"
        if ann.get("bold"):
            text = f"<strong>{text}</strong>"
        if ann.get("italic"):
            text = f"<em>{text}</em>"
        if ann.get("underline"):
            text = f"<u>{text}</u>"
        if ann.get("strikethrough"):
            text = f"<s>{text}</s>"
        color = ann.get("color", "default")
        if color != "default":
            if color.endswith("_background"):
                text = f'<span style="background:{color.replace("_background","")}">{text}</span>'
            else:
                text = f'<span style="color:{color}">{text}</span>'
        href = rt.get("href")
        if href:
            text = f'<a href="{href}" target="_blank">{text}</a>'
        parts.append(text)
    return "".join(parts)


_EDITABLE_TYPES = {
    "paragraph", "heading_1", "heading_2", "heading_3",
    "bulleted_list_item", "numbered_list_item", "quote",
    "to_do", "callout", "toggle", "code",
}


def _editable_span(btype, block_id, inner):
    if btype not in _EDITABLE_TYPES or not block_id:
        return inner
    return (
        f'<span class="nt-block-text" contenteditable="true" '
        f'data-block-id="{block_id}" data-block-type="{btype}">{inner}</span>'
    )


def get_content(page_id):
    """Get the HTML content of a Notion page."""
    result = notion_request("GET", f"https://api.notion.com/v1/blocks/{page_id}/children")
    html_parts = []
    for block in result.get("results", []):
        btype = block.get("type", "")
        bdata = block.get(btype, {})
        rich_text = bdata.get("rich_text", [])
        text = _rich_text_html(rich_text)
        block_id = block.get("id", "")
        editable = _editable_span(btype, block_id, text or "&#8203;")
        if btype == "to_do":
            checked = bdata.get("checked", False)
            chk = "checked" if checked else ""
            style = ' style="color:#999;text-decoration:line-through"' if checked else ''
            html_parts.append(f'<div class="nt-todo-block"{style}><input type="checkbox" {chk} data-block-id="{block_id}" class="nt-todo-checkbox" /> {editable}</div>')
        elif btype == "heading_1":
            html_parts.append(f"<h3>{editable}</h3>")
        elif btype == "heading_2":
            html_parts.append(f"<h4>{editable}</h4>")
        elif btype == "heading_3":
            html_parts.append(f"<h5>{editable}</h5>")
        elif btype == "bulleted_list_item":
            html_parts.append(f"<div>• {editable}</div>")
        elif btype == "numbered_list_item":
            html_parts.append(f"<div>‣ {editable}</div>")
        elif btype == "quote":
            html_parts.append(f'<blockquote style="border-left:3px solid #ddd;padding-left:10px;color:#666;margin:4px 0">{editable}</blockquote>')
        elif btype == "code":
            html_parts.append(f'<pre style="background:#f5f5f5;padding:8px;border-radius:4px;font-size:0.8rem;overflow-x:auto"><code>{editable}</code></pre>')
        elif btype == "divider":
            html_parts.append('<hr style="border:none;border-top:1px solid #e0e0e0;margin:8px 0">')
        elif btype == "callout":
            emoji = bdata.get("icon", {}).get("emoji", "💡")
            html_parts.append(f'<div style="background:#f9f9f9;border-radius:6px;padding:8px 12px;margin:4px 0">{emoji} {editable}</div>')
        elif btype == "toggle":
            html_parts.append(f"<details><summary>{editable}</summary></details>")
        elif btype == "image":
            url = bdata.get("file", bdata.get("external", {})).get("url", "")
            if url:
                html_parts.append(f'<img src="{url}" style="max-width:100%;border-radius:4px;margin:4px 0" />')
        elif btype == "paragraph":
            html_parts.append(f"<div>{editable}</div>")
        elif text:
            html_parts.append(f"<div>{text}</div>")
    return "\n".join(html_parts)


def update_block_text(block_id, block_type, text):
    """Overwrite the rich_text of a block with plain text."""
    if block_type not in _EDITABLE_TYPES:
        return {"ok": False, "error": f"type {block_type} not editable"}
    body = {block_type: {"rich_text": [{"type": "text", "text": {"content": text}}]}}
    notion_request("PATCH", f"https://api.notion.com/v1/blocks/{block_id}", body)
    return {"ok": True}


def toggle_block_todo(block_id, checked):
    """Toggle the checked state of a to_do block."""
    notion_request("PATCH", f"https://api.notion.com/v1/blocks/{block_id}", {
        "to_do": {"checked": checked}
    })
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
                result = complete_task(body["id"])
                self._send_json(result)
            elif action == "get_content":
                content = get_content(body["id"])
                self._send_json({"content": content})
            elif action == "toggle_block_todo":
                result = toggle_block_todo(body["block_id"], body["checked"])
                self._send_json(result)
            elif action == "update_block":
                result = update_block_text(body["block_id"], body["block_type"], body.get("text", ""))
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
