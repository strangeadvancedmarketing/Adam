"""
Adam Framework — SWARM Task Orchestration Runtime

File-based multi-agent coordination. Agents don't talk to each other —
they talk to the Vault. Tasks are files. Locks prevent double-processing.
The filesystem is the queue.

Usage:
    from adam.swarm import Swarm

    swarm = Swarm(vault_path="/path/to/vault")
    swarm.create_task("research", {"target": "Doctor Paver Corp", "source": "reddit"})

    # In an agent process:
    task = swarm.claim_next("research", agent_id="pattern_seeker")
    if task:
        result = do_work(task)
        swarm.complete_task(task.task_id, result)
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Task:
    """A task in the SWARM queue."""
    task_id: str
    task_type: str
    payload: dict[str, Any]
    status: str = "pending"  # pending, claimed, completed, failed
    created_at: str = ""
    claimed_by: str = ""
    claimed_at: str = ""
    completed_at: str = ""
    priority: int = 0  # higher = more urgent

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Task:
        return Task(**{k: v for k, v in data.items() if k in Task.__dataclass_fields__})

    @staticmethod
    def from_file(path: Path) -> Task:
        with open(path, "r", encoding="utf-8") as f:
            return Task.from_dict(json.load(f))


@dataclass
class AgentRegistration:
    """A registered agent in the SWARM."""
    agent_id: str
    agent_type: str  # What kind of tasks this agent handles
    description: str = ""
    registered_at: str = ""
    last_heartbeat: str = ""
    status: str = "active"  # active, paused, offline

    def __post_init__(self) -> None:
        if not self.registered_at:
            self.registered_at = datetime.now(timezone.utc).isoformat()


class Swarm:
    """
    File-based multi-agent task orchestration.

    The Vault directory structure:
        workspace/tasks/          <- task queue (JSON files)
        workspace/tasks/*.lock    <- claim locks
        workspace/output/         <- completed results
        workspace/agents.json     <- agent registry
    """

    def __init__(self, vault_path: str | Path) -> None:
        self.vault = Path(vault_path)
        self.tasks_dir = self.vault / "workspace" / "tasks"
        self.output_dir = self.vault / "workspace" / "output"
        self.agents_file = self.vault / "workspace" / "agents.json"

        # Ensure directories exist
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ── Task Management ────────────────────────────────────────

    def create_task(
        self,
        task_type: str,
        payload: dict[str, Any],
        priority: int = 0,
        task_id: str | None = None,
    ) -> Task:
        """Create a new task in the queue."""
        task = Task(
            task_id=task_id or uuid.uuid4().hex[:12],
            task_type=task_type,
            payload=payload,
            priority=priority,
        )
        task_file = self.tasks_dir / f"{task.task_id}.json"
        self._atomic_write(task_file, json.dumps(task.to_dict(), indent=2))
        return task

    def list_tasks(
        self,
        task_type: str | None = None,
        status: str | None = None,
    ) -> list[Task]:
        """List tasks, optionally filtered by type and/or status."""
        tasks: list[Task] = []
        for f in sorted(self.tasks_dir.glob("*.json")):
            if f.name == "agents.json":
                continue
            try:
                task = Task.from_file(f)
                if task_type and task.task_type != task_type:
                    continue
                if status and task.status != status:
                    continue
                tasks.append(task)
            except (json.JSONDecodeError, KeyError):
                continue
        return sorted(tasks, key=lambda t: (-t.priority, t.created_at))

    def get_task(self, task_id: str) -> Task | None:
        """Get a specific task by ID."""
        task_file = self.tasks_dir / f"{task_id}.json"
        if not task_file.exists():
            return None
        return Task.from_file(task_file)

    def claim_next(self, task_type: str, agent_id: str) -> Task | None:
        """
        Claim the next available task of the given type.
        Uses atomic lock file to prevent double-processing.
        Returns the claimed task or None if nothing available.
        """
        pending = self.list_tasks(task_type=task_type, status="pending")
        for task in pending:
            lock_file = self.tasks_dir / f"{task.task_id}.lock"
            # Atomic claim: try to create lock file
            if self._try_lock(lock_file, agent_id):
                task.status = "claimed"
                task.claimed_by = agent_id
                task.claimed_at = datetime.now(timezone.utc).isoformat()
                task_file = self.tasks_dir / f"{task.task_id}.json"
                self._atomic_write(task_file, json.dumps(task.to_dict(), indent=2))
                return task
        return None

    def complete_task(
        self,
        task_id: str,
        result: dict[str, Any],
        agent_id: str = "",
    ) -> None:
        """Mark a task as completed and write result to output."""
        task_file = self.tasks_dir / f"{task_id}.json"
        lock_file = self.tasks_dir / f"{task_id}.lock"

        if not task_file.exists():
            raise FileNotFoundError(f"Task {task_id} not found")

        task = Task.from_file(task_file)
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc).isoformat()

        # Write result to output directory
        output = {
            "task_id": task_id,
            "task_type": task.task_type,
            "completed_by": agent_id or task.claimed_by,
            "completed_at": task.completed_at,
            "original_payload": task.payload,
            "result": result,
        }
        output_file = self.output_dir / f"{task_id}_result.json"
        self._atomic_write(output_file, json.dumps(output, indent=2))

        # Clean up task and lock
        task_file.unlink(missing_ok=True)
        lock_file.unlink(missing_ok=True)

    def fail_task(self, task_id: str, error: str, agent_id: str = "") -> None:
        """Mark a task as failed. Removes lock so it can be retried."""
        task_file = self.tasks_dir / f"{task_id}.json"
        lock_file = self.tasks_dir / f"{task_id}.lock"

        if not task_file.exists():
            return

        task = Task.from_file(task_file)
        task.status = "failed"
        task.payload["_last_error"] = error
        task.payload["_failed_by"] = agent_id or task.claimed_by
        task.payload["_failed_at"] = datetime.now(timezone.utc).isoformat()

        # Reset to pending for retry, but keep error info
        task.status = "pending"
        task.claimed_by = ""
        task.claimed_at = ""
        self._atomic_write(task_file, json.dumps(task.to_dict(), indent=2))
        lock_file.unlink(missing_ok=True)

    def get_results(self, task_type: str | None = None) -> list[dict[str, Any]]:
        """Read completed results from the output directory."""
        results: list[dict[str, Any]] = []
        for f in sorted(self.output_dir.glob("*_result.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if task_type and data.get("task_type") != task_type:
                    continue
                results.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
        return results

    def cleanup_stale_locks(self, max_age_seconds: int = 3600) -> int:
        """Remove lock files older than max_age_seconds. Returns count removed."""
        now = time.time()
        removed = 0
        for lock_file in self.tasks_dir.glob("*.lock"):
            if now - lock_file.stat().st_mtime > max_age_seconds:
                task_id = lock_file.stem
                task_file = self.tasks_dir / f"{task_id}.json"
                if task_file.exists():
                    task = Task.from_file(task_file)
                    if task.status == "claimed":
                        task.status = "pending"
                        task.claimed_by = ""
                        task.claimed_at = ""
                        self._atomic_write(task_file, json.dumps(task.to_dict(), indent=2))
                lock_file.unlink(missing_ok=True)
                removed += 1
        return removed

    # ── Agent Registry ─────────────────────────────────────────

    def register_agent(self, agent_id: str, agent_type: str, description: str = "") -> None:
        """Register an agent in the SWARM."""
        agents = self._load_agents()
        agents[agent_id] = asdict(AgentRegistration(
            agent_id=agent_id,
            agent_type=agent_type,
            description=description,
        ))
        self._save_agents(agents)

    def heartbeat(self, agent_id: str) -> None:
        """Update an agent's heartbeat timestamp."""
        agents = self._load_agents()
        if agent_id in agents:
            agents[agent_id]["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
            agents[agent_id]["status"] = "active"
            self._save_agents(agents)

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        agents = self._load_agents()
        return list(agents.values())

    def deregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the registry."""
        agents = self._load_agents()
        agents.pop(agent_id, None)
        self._save_agents(agents)

    # ── Stats ──────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Get SWARM statistics."""
        all_tasks = self.list_tasks()
        results = self.get_results()
        agents = self.list_agents()
        return {
            "pending": sum(1 for t in all_tasks if t.status == "pending"),
            "claimed": sum(1 for t in all_tasks if t.status == "claimed"),
            "completed": len(results),
            "agents_registered": len(agents),
            "agents_active": sum(1 for a in agents if a.get("status") == "active"),
            "task_types": list(set(t.task_type for t in all_tasks)),
        }

    # ── Internal ───────────────────────────────────────────────

    def _try_lock(self, lock_file: Path, agent_id: str) -> bool:
        """Atomic lock file creation. Returns True if lock acquired."""
        tmp = lock_file.with_suffix(".tmp")
        try:
            # Write to temp file first
            tmp.write_text(json.dumps({
                "agent_id": agent_id,
                "locked_at": datetime.now(timezone.utc).isoformat(),
            }))
            # Atomic rename — first rename wins on all platforms
            if lock_file.exists():
                tmp.unlink(missing_ok=True)
                return False
            tmp.rename(lock_file)
            return True
        except (OSError, FileExistsError):
            tmp.unlink(missing_ok=True)
            return False

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write file atomically via temp + rename."""
        tmp = path.with_suffix(".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)

    def _load_agents(self) -> dict[str, Any]:
        if not self.agents_file.exists():
            return {}
        try:
            with open(self.agents_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_agents(self, agents: dict[str, Any]) -> None:
        self._atomic_write(self.agents_file, json.dumps(agents, indent=2))
