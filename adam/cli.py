"""
Adam Framework — CLI Tool

Entry point for the Adam Framework. Provides commands to initialize a vault,
start/stop SENTINEL, check status, validate config, and manage the SWARM.

Usage:
    adam init                  # Interactive vault setup
    adam start                 # Launch SENTINEL daemon
    adam stop                  # Stop SENTINEL daemon
    adam status                # Show framework health
    adam config validate       # Validate configuration
    adam reconcile             # Run memory reconciliation manually
    adam swarm stats           # Show SWARM statistics
    adam swarm tasks           # List pending tasks
    adam swarm create TYPE     # Create a new task
    adam events pending        # Show pending events
    adam webhook start [PORT]  # Start webhook receiver
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from adam import __version__


def get_vault_path() -> Path:
    """Get vault path from env or default."""
    return Path(os.environ.get("ADAM_VAULT_PATH", Path.home() / "AdamsVault"))


def get_template_dir() -> Path:
    """Get the template directory shipped with the package."""
    return Path(__file__).parent.parent / "vault-templates"


def get_engine_dir() -> Path:
    """Get the engine template directory."""
    return Path(__file__).parent.parent / "engine"


# ── INIT ───────────────────────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new Adam vault."""
    vault = Path(args.path) if args.path else get_vault_path()
    print(f"Adam Framework v{__version__} — Vault Initialization")
    print(f"Target: {vault}\n")

    if vault.exists() and any(vault.iterdir()):
        if not args.force:
            print(f"Directory {vault} already exists and is not empty.")
            print("Use --force to overwrite, or choose a different path.")
            return 1

    # Create directory structure
    dirs = [
        vault,
        vault / "workspace",
        vault / "workspace" / "memory",
        vault / "workspace" / "tasks",
        vault / "workspace" / "output",
        vault / "workspace" / "events",
        vault / "workspace" / "events" / "processed",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {d}")

    # Copy vault templates if available
    template_dir = get_template_dir()
    if template_dir.exists():
        for tmpl in template_dir.glob("*.template.*"):
            dest_name = tmpl.name.replace(".template", "")
            dest = vault / dest_name
            if not dest.exists() or args.force:
                shutil.copy2(tmpl, dest)
                print(f"  Template: {dest_name}")

    # Copy engine templates
    engine_dir = get_engine_dir()
    tools_dest = vault / "tools"
    tools_dest.mkdir(exist_ok=True)
    if engine_dir.exists():
        for tmpl in engine_dir.glob("*.template.*"):
            dest_name = tmpl.name.replace(".template", "")
            dest = vault / "engine" / dest_name
            dest.parent.mkdir(exist_ok=True)
            if not dest.exists() or args.force:
                shutil.copy2(tmpl, dest)
                print(f"  Engine: {dest_name}")

    # Copy tools
    tools_src = Path(__file__).parent.parent / "tools"
    if tools_src.exists():
        for tool in tools_src.glob("*.py"):
            dest = tools_dest / tool.name
            if not dest.exists() or args.force:
                shutil.copy2(tool, dest)
                print(f"  Tool: {tool.name}")

    # Write initial config
    config = {
        "vault_path": str(vault),
        "provider": "auto",
        "version": __version__,
        "created_at": datetime.now().isoformat(),
    }
    config_file = vault / "adam.json"
    if not config_file.exists() or args.force:
        config_file.write_text(json.dumps(config, indent=2))
        print(f"  Config: adam.json")

    # Write TODAY.md
    today_file = vault / "workspace" / "TODAY.md"
    today_file.write_text(datetime.now().strftime("%Y-%m-%d"))

    print(f"\nVault initialized at {vault}")
    print("\nNext steps:")
    print(f"  1. Set your LLM provider: export GEMINI_API_KEY=... (or OPENAI_API_KEY, etc.)")
    print(f"  2. Edit {vault}/SOUL.md to define your AI's identity")
    print(f"  3. Edit {vault}/CORE_MEMORY.md with your project state")
    print(f"  4. Run: adam start")
    return 0


# ── START / STOP ───────────────────────────────────────────────────────

def cmd_start(args: argparse.Namespace) -> int:
    """Start SENTINEL daemon."""
    vault = get_vault_path()
    if not vault.exists():
        print(f"No vault found at {vault}. Run 'adam init' first.")
        return 1

    system = platform.system()
    if system == "Windows":
        sentinel = vault / "engine" / "SENTINEL.ps1"
        if not sentinel.exists():
            sentinel = get_engine_dir() / "SENTINEL.template.ps1"
        if not sentinel.exists():
            print("SENTINEL script not found. Run 'adam init' first.")
            return 1
        print(f"Starting SENTINEL from {sentinel}...")
        subprocess.Popen(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(sentinel)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        sentinel = vault / "engine" / "SENTINEL.sh"
        if not sentinel.exists():
            sentinel = get_engine_dir() / "SENTINEL.template.sh"
        if not sentinel.exists():
            print("SENTINEL script not found. Run 'adam init' first.")
            return 1
        print(f"Starting SENTINEL from {sentinel}...")
        subprocess.Popen(
            ["bash", str(sentinel)],
            start_new_session=True,
        )

    print("SENTINEL launched. Use 'adam status' to check health.")
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    """Stop SENTINEL daemon."""
    system = platform.system()
    if system == "Windows":
        os.system('taskkill /F /FI "WINDOWTITLE eq SENTINEL*" >nul 2>&1')
        print("SENTINEL stop signal sent.")
    else:
        os.system("pkill -f SENTINEL 2>/dev/null")
        print("SENTINEL stop signal sent.")
    return 0


# ── STATUS ─────────────────────────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> int:
    """Show framework health status."""
    vault = get_vault_path()
    print(f"Adam Framework v{__version__}")
    print(f"Vault: {vault}")
    print(f"Exists: {'yes' if vault.exists() else 'NO'}")

    if not vault.exists():
        print("\nNo vault found. Run 'adam init' to get started.")
        return 1

    # Check key files
    key_files = {
        "SOUL.md": vault / "SOUL.md",
        "CORE_MEMORY.md": vault / "CORE_MEMORY.md",
        "adam.json": vault / "adam.json",
        "TODAY.md": vault / "workspace" / "TODAY.md",
    }
    print("\nKey Files:")
    for name, path in key_files.items():
        status = "OK" if path.exists() else "MISSING"
        size = f"({path.stat().st_size} bytes)" if path.exists() else ""
        print(f"  {name}: {status} {size}")

    # Check provider
    print("\nProvider:")
    from adam.providers import ProviderConfig
    try:
        cfg = ProviderConfig.from_env()
        print(f"  Detected: {cfg.provider} ({cfg.model})")
    except Exception:
        print("  No provider configured. Set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY.")

    # Check SWARM
    tasks_dir = vault / "workspace" / "tasks"
    output_dir = vault / "workspace" / "output"
    if tasks_dir.exists():
        pending = len(list(tasks_dir.glob("*.json")))
        completed = len(list(output_dir.glob("*_result.json"))) if output_dir.exists() else 0
        print(f"\nSWARM:")
        print(f"  Pending tasks: {pending}")
        print(f"  Completed results: {completed}")

    # Check events
    events_dir = vault / "workspace" / "events"
    if events_dir.exists():
        pending_events = len([f for f in events_dir.glob("*.json") if f.name != "handlers.json"])
        print(f"\nEvents:")
        print(f"  Pending: {pending_events}")

    # Check memory logs
    memory_dir = vault / "workspace" / "memory"
    if memory_dir.exists():
        logs = sorted(memory_dir.glob("????-??-??.md"))
        print(f"\nMemory:")
        print(f"  Daily logs: {len(logs)}")
        if logs:
            print(f"  Latest: {logs[-1].name}")

    return 0


# ── CONFIG ─────────────────────────────────────────────────────────────

def cmd_config_validate(args: argparse.Namespace) -> int:
    """Validate framework configuration."""
    vault = get_vault_path()
    errors: list[str] = []
    warnings: list[str] = []

    if not vault.exists():
        errors.append(f"Vault not found at {vault}")
    else:
        required = ["SOUL.md", "CORE_MEMORY.md"]
        for name in required:
            if not (vault / name).exists():
                warnings.append(f"Missing: {name} (copy from vault-templates/)")

        config_file = vault / "adam.json"
        if config_file.exists():
            try:
                json.loads(config_file.read_text())
                print("  adam.json: valid JSON")
            except json.JSONDecodeError as e:
                errors.append(f"adam.json is invalid JSON: {e}")

    # Check provider
    from adam.providers import ProviderConfig
    try:
        cfg = ProviderConfig.from_env()
        print(f"  Provider: {cfg.provider} ({cfg.model})")
    except Exception:
        warnings.append("No LLM provider configured (set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY)")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  [ERROR] {e}")
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  [WARN] {w}")
    if not errors and not warnings:
        print("\nAll checks passed.")

    return 1 if errors else 0


# ── RECONCILE ──────────────────────────────────────────────────────────

def cmd_reconcile(args: argparse.Namespace) -> int:
    """Run memory reconciliation manually."""
    vault = get_vault_path()
    reconcile_script = vault / "tools" / "reconcile_memory.py"
    if not reconcile_script.exists():
        reconcile_script = Path(__file__).parent.parent / "tools" / "reconcile_memory.py"
    if not reconcile_script.exists():
        print("reconcile_memory.py not found. Run 'adam init' first.")
        return 1

    cmd = [sys.executable, str(reconcile_script), "--vault-path", str(vault)]
    if args.dry_run:
        cmd.append("--dry-run")
    print(f"Running reconciliation...")
    return subprocess.call(cmd)


# ── SWARM ──────────────────────────────────────────────────────────────

def cmd_swarm_stats(args: argparse.Namespace) -> int:
    """Show SWARM statistics."""
    from adam.swarm import Swarm
    swarm = Swarm(get_vault_path())
    stats = swarm.stats()
    print("SWARM Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    return 0


def cmd_swarm_tasks(args: argparse.Namespace) -> int:
    """List pending SWARM tasks."""
    from adam.swarm import Swarm
    swarm = Swarm(get_vault_path())
    tasks = swarm.list_tasks(status=args.status if args.status != "all" else None)
    if not tasks:
        print("No tasks found.")
        return 0
    for task in tasks:
        print(f"  [{task.status}] {task.task_id} ({task.task_type}) — priority {task.priority}")
        if task.claimed_by:
            print(f"           claimed by {task.claimed_by}")
    return 0


def cmd_swarm_create(args: argparse.Namespace) -> int:
    """Create a new SWARM task."""
    from adam.swarm import Swarm
    swarm = Swarm(get_vault_path())
    payload = {}
    if args.payload:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError:
            payload = {"description": args.payload}
    task = swarm.create_task(
        task_type=args.type,
        payload=payload,
        priority=args.priority,
    )
    print(f"Created task {task.task_id} (type={task.task_type}, priority={task.priority})")
    return 0


# ── EVENTS ─────────────────────────────────────────────────────────────

def cmd_events_pending(args: argparse.Namespace) -> int:
    """Show pending events."""
    from adam.events import EventBus
    bus = EventBus(get_vault_path())
    events = bus.poll()
    if not events:
        print("No pending events.")
        return 0
    for event in events:
        print(f"  [{event.event_type}] {event.event_id} from {event.source} @ {event.timestamp}")
    return 0


def cmd_webhook_start(args: argparse.Namespace) -> int:
    """Start the webhook receiver."""
    from adam.events import create_webhook_app
    server, bus = create_webhook_app(get_vault_path())
    port = args.port or 9876
    server.server_address = ("127.0.0.1", port)
    server.server_bind()
    server.server_activate()
    print(f"Webhook receiver listening on http://127.0.0.1:{port}/webhook")
    print("POST events to /webhook, GET /events for pending count, GET /health for status.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
    return 0


# ── MAIN ───────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adam",
        description="Adam Framework — Autonomous AI Agent Harness",
    )
    parser.add_argument("--version", action="version", version=f"adam {__version__}")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = sub.add_parser("init", help="Initialize a new vault")
    p_init.add_argument("--path", help="Vault path (default: ~/AdamsVault)")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing files")

    # start
    sub.add_parser("start", help="Start SENTINEL daemon")

    # stop
    sub.add_parser("stop", help="Stop SENTINEL daemon")

    # status
    sub.add_parser("status", help="Show framework health")

    # config
    p_config = sub.add_parser("config", help="Configuration management")
    config_sub = p_config.add_subparsers(dest="config_command")
    config_sub.add_parser("validate", help="Validate configuration")

    # reconcile
    p_rec = sub.add_parser("reconcile", help="Run memory reconciliation")
    p_rec.add_argument("--dry-run", action="store_true", help="Preview without writing")

    # swarm
    p_swarm = sub.add_parser("swarm", help="SWARM task management")
    swarm_sub = p_swarm.add_subparsers(dest="swarm_command")
    swarm_sub.add_parser("stats", help="Show statistics")
    p_tasks = swarm_sub.add_parser("tasks", help="List tasks")
    p_tasks.add_argument("--status", default="all", help="Filter by status")
    p_create = swarm_sub.add_parser("create", help="Create a task")
    p_create.add_argument("type", help="Task type")
    p_create.add_argument("--payload", help="Task payload (JSON string or text)")
    p_create.add_argument("--priority", type=int, default=0, help="Priority (higher=urgent)")

    # events
    p_events = sub.add_parser("events", help="Event management")
    events_sub = p_events.add_subparsers(dest="events_command")
    events_sub.add_parser("pending", help="Show pending events")

    # webhook
    p_webhook = sub.add_parser("webhook", help="Webhook receiver")
    webhook_sub = p_webhook.add_subparsers(dest="webhook_command")
    p_wh_start = webhook_sub.add_parser("start", help="Start webhook receiver")
    p_wh_start.add_argument("--port", type=int, default=9876, help="Port (default: 9876)")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "init": cmd_init,
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "reconcile": cmd_reconcile,
    }

    if args.command in commands:
        return commands[args.command](args)

    if args.command == "config":
        if args.config_command == "validate":
            return cmd_config_validate(args)
        parser.parse_args(["config", "--help"])

    if args.command == "swarm":
        swarm_cmds = {"stats": cmd_swarm_stats, "tasks": cmd_swarm_tasks, "create": cmd_swarm_create}
        if args.swarm_command in swarm_cmds:
            return swarm_cmds[args.swarm_command](args)
        parser.parse_args(["swarm", "--help"])

    if args.command == "events":
        if args.events_command == "pending":
            return cmd_events_pending(args)
        parser.parse_args(["events", "--help"])

    if args.command == "webhook":
        if args.webhook_command == "start":
            return cmd_webhook_start(args)
        parser.parse_args(["webhook", "--help"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
