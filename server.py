#!/usr/bin/env python3
"""Dev server: static files, data persistence, and voice-to-tasks API."""

import json, os, http.server, urllib.request, uuid, re

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "data.json")
ARCHIVE_FILE = os.path.join(BASE, "archive.json")

# Load API keys from .env
def load_env():
    env_path = os.path.join(BASE, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_DB_ID = "24d95563-22a9-484f-9db0-e93d9bbca600"
NOTION_VERSION = "2022-06-28"

CLAUDE_SYSTEM_PROMPT = """You are a task parser for a personal desk/dashboard app. The user will give you a transcription of them describing tasks for their day.

Parse it into a JSON array of task objects. Each task is one of:

1. A to-do: { "type": "todo", "label": "<task description>", "checked": false, "notes": "" }
2. A timer: { "type": "timer", "label": "<task description>", "totalSeconds": <seconds>, "elapsed": 0, "running": false, "notes": "" }

Use "timer" ONLY when the user explicitly mentions a duration (e.g., "25 minutes", "1 hour focus session"). Otherwise use "todo".

For to-do labels, be concise but include relevant details like names, times, or locations the user mentioned. If the user says something like "meeting with Sarah at 2pm", the label should be "Meeting with Sarah at 2pm".

Return ONLY the JSON array, no markdown fences, no explanation."""


def _parse_multipart(body, content_type):
    """Parse multipart/form-data to extract the audio file."""
    boundary = content_type.split("boundary=")[1].strip()
    if boundary.startswith('"') and boundary.endswith('"'):
        boundary = boundary[1:-1]
    boundary = boundary.encode()

    parts = body.split(b"--" + boundary)
    for part in parts:
        if b"Content-Disposition" not in part:
            continue
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue
        headers = part[:header_end].decode("utf-8", errors="replace")
        data = part[header_end + 4:]
        if data.endswith(b"\r\n"):
            data = data[:-2]
        if 'name="audio"' in headers:
            # Extract filename if present
            fname_match = re.search(r'filename="([^"]*)"', headers)
            filename = fname_match.group(1) if fname_match else "audio.webm"
            # Extract content type
            ct_match = re.search(r"Content-Type:\s*(.+)", headers)
            file_ct = ct_match.group(1).strip() if ct_match else "audio/webm"
            return data, filename, file_ct
    return None, None, None


def call_whisper(audio_data, filename, file_content_type):
    """Send audio to OpenAI Whisper API and return transcription text."""
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {file_content_type}\r\n\r\n"
    ).encode() + audio_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["text"]


def call_claude(transcript):
    """Send transcript to Claude and return parsed task list."""
    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1024,
        "system": CLAUDE_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": transcript}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    text = result["content"][0]["text"].strip()
    # Strip markdown fences if Claude included them
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return json.loads(text)


def notion_request(method, url, body=None):
    """Make a request to the Notion API."""
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def notion_list_tasks():
    body = {
        "filter": {
            "property": "Done",
            "status": {"does_not_equal": "Done"}
        },
        "sorts": [
            {"property": "Due", "direction": "ascending"},
            {"timestamp": "created_time", "direction": "descending"}
        ],
        "page_size": 50
    }
    result = notion_request("POST", f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query", body)
    tasks = []
    for page in result.get("results", []):
        props = page["properties"]
        title_prop = props.get("Task", props.get("Name", {}))
        title = ""
        if title_prop.get("title"):
            title = "".join(t.get("plain_text", "") for t in title_prop["title"])
        status = ""
        if props.get("Done", {}).get("status"):
            status = props["Done"]["status"].get("name", "")
        due = None
        if props.get("Due", {}).get("date"):
            due = props["Due"]["date"].get("start")
        tasks.append({"id": page["id"], "title": title, "status": status, "due": due, "url": page.get("url", "")})
    return tasks


def notion_create_task(title, due=None):
    properties = {
        "Task": {"title": [{"text": {"content": title}}]},
        "Done": {"status": {"name": "Not started"}},
    }
    if due:
        properties["Due"] = {"date": {"start": due}}
    body = {"parent": {"database_id": NOTION_DB_ID}, "properties": properties}
    result = notion_request("POST", "https://api.notion.com/v1/pages", body)
    return {"id": result["id"], "title": title, "status": "Not started", "due": due}


def notion_update_task(page_id, updates):
    properties = {}
    if "title" in updates:
        properties["Task"] = {"title": [{"text": {"content": updates["title"]}}]}
    if "status" in updates:
        properties["Done"] = {"status": {"name": updates["status"]}}
    if "due" in updates:
        properties["Due"] = {"date": {"start": updates["due"]} if updates["due"] else None}
    notion_request("PATCH", f"https://api.notion.com/v1/pages/{page_id}", {"properties": properties})
    return {"ok": True}


def notion_archive_task(page_id):
    notion_request("PATCH", f"https://api.notion.com/v1/pages/{page_id}", {"archived": True})
    return {"ok": True}


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/items":
            self._send_json(self._read(DATA_FILE, []))
        elif self.path == "/api/archive":
            self._send_json(self._read(ARCHIVE_FILE, []))
        elif self.path == "/api/notion":
            try:
                tasks = notion_list_tasks()
                self._send_json({"tasks": tasks})
            except Exception as e:
                print(f"[notion] Error: {e}")
                self._send_json({"error": str(e)}, status=500)
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")

        if self.path == "/api/voice":
            self._handle_voice(content_length, content_type)
            return

        if self.path == "/api/notion":
            self._handle_notion(content_length)
            return

        body = self.rfile.read(content_length)
        data = json.loads(body)
        if self.path == "/api/items":
            self._write(DATA_FILE, data)
            self._send_json({"ok": True})
        elif self.path == "/api/archive":
            archive = self._read(ARCHIVE_FILE, [])
            if isinstance(data, list):
                archive.extend(data)
            else:
                archive.append(data)
            self._write(ARCHIVE_FILE, archive)
            self._send_json({"ok": True})
        else:
            self.send_error(404)

    def _handle_notion(self, content_length):
        try:
            body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
            action = body.get("action", "create")
            if action == "create":
                result = notion_create_task(body.get("title", ""), body.get("due"))
                self._send_json(result)
            elif action == "update":
                result = notion_update_task(body["id"], body.get("updates", {}))
                self._send_json(result)
            elif action == "archive":
                result = notion_archive_task(body["id"])
                self._send_json(result)
            elif action == "complete":
                result = notion_update_task(body["id"], {"status": "Done"})
                self._send_json(result)
            else:
                self._send_json({"error": f"Unknown action: {action}"}, status=400)
        except Exception as e:
            print(f"[notion] Error: {e}")
            self._send_json({"error": str(e)}, status=500)

    def _handle_voice(self, content_length, content_type):
        try:
            body = self.rfile.read(content_length)
            audio_data, filename, file_ct = _parse_multipart(body, content_type)
            if audio_data is None:
                self._send_json({"error": "No audio data found"}, status=400)
                return

            print(f"[voice] Received {len(audio_data)} bytes of audio")

            # Step 1: Transcribe with Whisper
            transcript = call_whisper(audio_data, filename, file_ct)
            print(f"[voice] Transcript: {transcript}")

            # Step 2: Parse with Claude
            tasks = call_claude(transcript)
            print(f"[voice] Parsed {len(tasks)} tasks")

            self._send_json({"transcript": transcript, "tasks": tasks})
        except Exception as e:
            print(f"[voice] Error: {e}")
            self._send_json({"error": str(e)}, status=500)

    def _read(self, path, default):
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return default

    def _write(self, path, obj):
        with open(path, "w") as f:
            json.dump(obj, f, indent=2)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    os.chdir(BASE)
    port = int(os.environ.get("PORT", 8000))
    if not OPENAI_API_KEY:
        print("WARNING: OPENAI_API_KEY not set in .env")
    if not ANTHROPIC_API_KEY:
        print("WARNING: ANTHROPIC_API_KEY not set in .env")
    server = http.server.HTTPServer(("", port), Handler)
    print(f"Serving on http://localhost:{port}")
    server.serve_forever()
