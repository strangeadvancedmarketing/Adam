"""
Adam Framework — Event System

Lightweight event bus with webhook receiver for event-driven agent triggers.
Agents subscribe to event types. External systems push events via webhooks.
SENTINEL polls for file-based events on its regular loop.

Supports two modes:
  1. File-based events (default): Write JSON to workspace/events/
  2. HTTP webhook receiver: POST to localhost:port/webhook

Usage:
    from adam.events import EventBus, Event

    bus = EventBus(vault_path="/path/to/vault")

    # Emit an event (writes to filesystem)
    bus.emit(Event(event_type="github.push", source="webhook", payload={...}))

    # Poll for unprocessed events
    for event in bus.poll(event_type="github.push"):
        handle(event)
        bus.ack(event.event_id)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Event:
    """An event in the system."""
    event_type: str  # e.g. "github.push", "email.received", "schedule.cron"
    source: str = ""  # e.g. "webhook", "sentinel", "manual"
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = ""
    timestamp: str = ""
    processed: bool = False

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = uuid.uuid4().hex[:12]
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Event:
        return Event(**{k: v for k, v in data.items() if k in Event.__dataclass_fields__})


class EventBus:
    """
    File-based event bus for the Adam Framework.

    Events are JSON files in workspace/events/.
    Processed events move to workspace/events/processed/.
    """

    def __init__(self, vault_path: str | Path) -> None:
        self.vault = Path(vault_path)
        self.events_dir = self.vault / "workspace" / "events"
        self.processed_dir = self.events_dir / "processed"
        self.handlers_file = self.events_dir / "handlers.json"

        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def emit(self, event: Event) -> Event:
        """Emit an event to the bus (writes to filesystem)."""
        event_file = self.events_dir / f"{event.event_id}.json"
        self._atomic_write(event_file, json.dumps(event.to_dict(), indent=2))
        return event

    def poll(
        self,
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[Event]:
        """Poll for unprocessed events, optionally filtered by type."""
        events: list[Event] = []
        for f in sorted(self.events_dir.glob("*.json")):
            if f.name == "handlers.json":
                continue
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                event = Event.from_dict(data)
                if event.processed:
                    continue
                if event_type and event.event_type != event_type:
                    continue
                events.append(event)
                if len(events) >= limit:
                    break
            except (json.JSONDecodeError, KeyError):
                continue
        return events

    def ack(self, event_id: str) -> None:
        """Acknowledge (mark as processed) an event. Moves to processed dir."""
        event_file = self.events_dir / f"{event_id}.json"
        if not event_file.exists():
            return
        dest = self.processed_dir / f"{event_id}.json"
        try:
            with open(event_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["processed"] = True
            data["processed_at"] = datetime.now(timezone.utc).isoformat()
            self._atomic_write(dest, json.dumps(data, indent=2))
            event_file.unlink(missing_ok=True)
        except (json.JSONDecodeError, OSError):
            event_file.unlink(missing_ok=True)

    def pending_count(self, event_type: str | None = None) -> int:
        """Count unprocessed events."""
        return len(self.poll(event_type=event_type, limit=9999))

    def register_handler(self, event_type: str, handler_name: str, action: str) -> None:
        """
        Register an event handler mapping.
        Handlers define what should happen when an event of a given type arrives.
        This is a configuration file — actual execution is done by SENTINEL or agents.
        """
        handlers = self._load_handlers()
        if event_type not in handlers:
            handlers[event_type] = []
        handlers[event_type].append({
            "handler": handler_name,
            "action": action,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        })
        self._save_handlers(handlers)

    def get_handlers(self, event_type: str) -> list[dict[str, Any]]:
        """Get registered handlers for an event type."""
        handlers = self._load_handlers()
        return handlers.get(event_type, [])

    def cleanup_processed(self, max_age_days: int = 7) -> int:
        """Remove processed events older than max_age_days."""
        import time
        now = time.time()
        max_age_seconds = max_age_days * 86400
        removed = 0
        for f in self.processed_dir.glob("*.json"):
            if now - f.stat().st_mtime > max_age_seconds:
                f.unlink(missing_ok=True)
                removed += 1
        return removed

    # ── Internal ───────────────────────────────────────────────

    def _atomic_write(self, path: Path, content: str) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)

    def _load_handlers(self) -> dict[str, list[dict[str, Any]]]:
        if not self.handlers_file.exists():
            return {}
        try:
            with open(self.handlers_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_handlers(self, handlers: dict[str, list[dict[str, Any]]]) -> None:
        self._atomic_write(self.handlers_file, json.dumps(handlers, indent=2))


def create_webhook_app(vault_path: str | Path) -> Any:
    """
    Create a minimal HTTP webhook receiver using the standard library.
    Returns an HTTPServer instance. Run with server.serve_forever().

    POST /webhook with JSON body:
        {"event_type": "github.push", "source": "github", "payload": {...}}

    GET /events returns pending event count.
    GET /health returns OK.
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler

    bus = EventBus(vault_path)

    class WebhookHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path != "/webhook":
                self.send_response(404)
                self.end_headers()
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body)
                event = Event(
                    event_type=data.get("event_type", "unknown"),
                    source=data.get("source", "webhook"),
                    payload=data.get("payload", {}),
                )
                bus.emit(event)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "accepted",
                    "event_id": event.event_id,
                }).encode())
            except (json.JSONDecodeError, KeyError) as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        def do_GET(self) -> None:
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            elif self.path == "/events":
                count = bus.pending_count()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"pending": count}).encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            pass  # Suppress default logging

    return HTTPServer(("127.0.0.1", 0), WebhookHandler), bus
