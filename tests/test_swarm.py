"""Tests for adam.swarm module."""

import json
import tempfile
from pathlib import Path

import pytest

from adam.swarm import Swarm, Task


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    return tmp_path / "vault"


@pytest.fixture
def swarm(vault: Path) -> Swarm:
    return Swarm(vault)


class TestSwarmInit:
    def test_creates_directories(self, swarm: Swarm, vault: Path) -> None:
        assert (vault / "workspace" / "tasks").exists()
        assert (vault / "workspace" / "output").exists()


class TestTaskLifecycle:
    def test_create_task(self, swarm: Swarm) -> None:
        task = swarm.create_task("research", {"target": "test"})
        assert task.task_id
        assert task.task_type == "research"
        assert task.status == "pending"

    def test_list_tasks(self, swarm: Swarm) -> None:
        swarm.create_task("research", {"target": "a"})
        swarm.create_task("build", {"target": "b"})
        assert len(swarm.list_tasks()) == 2
        assert len(swarm.list_tasks(task_type="research")) == 1

    def test_claim_and_complete(self, swarm: Swarm) -> None:
        swarm.create_task("research", {"target": "test"}, priority=1)
        task = swarm.claim_next("research", agent_id="agent_1")
        assert task is not None
        assert task.status == "claimed"
        assert task.claimed_by == "agent_1"

        swarm.complete_task(task.task_id, {"findings": "done"}, agent_id="agent_1")
        results = swarm.get_results()
        assert len(results) == 1
        assert results[0]["result"]["findings"] == "done"

    def test_claim_prevents_double_claim(self, swarm: Swarm) -> None:
        swarm.create_task("research", {"target": "test"})
        task1 = swarm.claim_next("research", agent_id="agent_1")
        task2 = swarm.claim_next("research", agent_id="agent_2")
        assert task1 is not None
        assert task2 is None

    def test_fail_task_resets_to_pending(self, swarm: Swarm) -> None:
        swarm.create_task("research", {"target": "test"}, task_id="t1")
        swarm.claim_next("research", agent_id="agent_1")
        swarm.fail_task("t1", "connection timeout", agent_id="agent_1")
        task = swarm.get_task("t1")
        assert task is not None
        assert task.status == "pending"
        assert task.payload["_last_error"] == "connection timeout"

    def test_priority_ordering(self, swarm: Swarm) -> None:
        swarm.create_task("research", {"target": "low"}, priority=0)
        swarm.create_task("research", {"target": "high"}, priority=10)
        task = swarm.claim_next("research", agent_id="agent_1")
        assert task is not None
        assert task.payload["target"] == "high"


class TestAgentRegistry:
    def test_register_and_list(self, swarm: Swarm) -> None:
        swarm.register_agent("seeker", "research", description="Reddit monitor")
        agents = swarm.list_agents()
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "seeker"

    def test_heartbeat(self, swarm: Swarm) -> None:
        swarm.register_agent("seeker", "research")
        swarm.heartbeat("seeker")
        agents = swarm.list_agents()
        assert agents[0]["last_heartbeat"] != ""

    def test_deregister(self, swarm: Swarm) -> None:
        swarm.register_agent("seeker", "research")
        swarm.deregister_agent("seeker")
        assert len(swarm.list_agents()) == 0


class TestStats:
    def test_stats(self, swarm: Swarm) -> None:
        swarm.create_task("research", {"target": "a"})
        swarm.create_task("build", {"target": "b"})
        stats = swarm.stats()
        assert stats["pending"] == 2
        assert stats["claimed"] == 0
        assert set(stats["task_types"]) == {"research", "build"}
