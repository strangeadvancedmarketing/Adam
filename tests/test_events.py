"""Tests for adam.events module."""

from pathlib import Path

import pytest

from adam.events import Event, EventBus


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    return tmp_path / "vault"


@pytest.fixture
def bus(vault: Path) -> EventBus:
    return EventBus(vault)


class TestEventBus:
    def test_emit_and_poll(self, bus: EventBus) -> None:
        bus.emit(Event(event_type="test.event", source="unit_test", payload={"key": "value"}))
        events = bus.poll()
        assert len(events) == 1
        assert events[0].event_type == "test.event"

    def test_poll_filters_by_type(self, bus: EventBus) -> None:
        bus.emit(Event(event_type="github.push", source="gh"))
        bus.emit(Event(event_type="email.received", source="gmail"))
        assert len(bus.poll(event_type="github.push")) == 1
        assert len(bus.poll(event_type="email.received")) == 1

    def test_ack_moves_to_processed(self, bus: EventBus) -> None:
        event = bus.emit(Event(event_type="test", source="test"))
        assert bus.pending_count() == 1
        bus.ack(event.event_id)
        assert bus.pending_count() == 0
        assert (bus.processed_dir / f"{event.event_id}.json").exists()

    def test_pending_count(self, bus: EventBus) -> None:
        bus.emit(Event(event_type="a", source="test"))
        bus.emit(Event(event_type="b", source="test"))
        assert bus.pending_count() == 2
        assert bus.pending_count(event_type="a") == 1


class TestEventHandlers:
    def test_register_and_get_handlers(self, bus: EventBus) -> None:
        bus.register_handler("github.push", "deploy_agent", "run deployment")
        handlers = bus.get_handlers("github.push")
        assert len(handlers) == 1
        assert handlers[0]["handler"] == "deploy_agent"

    def test_no_handlers_returns_empty(self, bus: EventBus) -> None:
        assert bus.get_handlers("nonexistent") == []
