"""Vercel serverless function: voice → Whisper transcription → Claude task parsing."""

import json, os, re, uuid
from http.server import BaseHTTPRequestHandler
import urllib.request

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

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
            fname_match = re.search(r'filename="([^"]*)"', headers)
            filename = fname_match.group(1) if fname_match else "audio.webm"
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
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return json.loads(text)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            content_type = self.headers.get("Content-Type", "")
            body = self.rfile.read(content_length)

            audio_data, filename, file_ct = _parse_multipart(body, content_type)
            if audio_data is None:
                self._send_json({"error": "No audio data found"}, 400)
                return

            transcript = call_whisper(audio_data, filename, file_ct)
            tasks = call_claude(transcript)
            self._send_json({"transcript": transcript, "tasks": tasks})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
