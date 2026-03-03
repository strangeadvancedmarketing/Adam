#!/usr/bin/env python3
"""
Adam Framework — Legacy Importer (Step 1 of 2)
Extracts facts from your AI conversation history into a reviewable JSON file.
Run this first. Review the output. Then run ingest_triples.ps1 to load into the neural graph.

Supports:
  - Claude export zip  (claude.ai → Settings → Export Data)
  - Claude conversations.json (extracted from zip)
  - ChatGPT export zip (chatgpt.com → Settings → Data Controls → Export)
  - ChatGPT conversations.json (extracted from zip)

Usage:
  python legacy_importer.py --source path/to/export.zip --vault-path C:/YourVault
  python legacy_importer.py --source path/to/conversations.json --format claude --vault-path C:/YourVault
  python legacy_importer.py --source path/to/conversations.json --format chatgpt --vault-path C:/YourVault

Output:
  <vault-path>/imports/extracted_triples.json  -- review before ingesting
  <vault-path>/imports/extraction_report.txt   -- summary of what was found
"""

import re
import json
import zipfile
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime


# ── NOISE FILTER ─────────────────────────────────────────────────────────────
# Short filler messages that add no signal to the neural graph
_NOISE_RE = re.compile(
    r'^(hi|hello|hey|thanks|thank you|sure|okay|ok|got it|sounds good|'
    r'great|perfect|yes|no|yep|nope|yup|absolutely|understood|noted|'
    r'cool|nice|awesome|alright|sounds good|will do)[.!,]?\s*$',
    re.IGNORECASE
)

# ── EXTRACTION PATTERNS ───────────────────────────────────────────────────────
# Each tuple: (regex_pattern, default_subject_or_None, predicate_label)
# If default_subject is None, subject is extracted from the match itself.
# USER_NAME placeholder is replaced at runtime with --user-name arg.
_PATTERNS_TEMPLATE = [
    # Decisions
    (r"(?:i|we|USER_NAME)\s+decided\s+(?:to\s+)?(?:use\s+|switch\s+to\s+)?(.{5,50})",      "USER_NAME", "decided"),
    (r"(?:switched?|migrated?|moved?)\s+to\s+([\w][\w\s\-\.]{2,35})",                        "USER_NAME", "switched_to"),
    (r"(?:switched?\s+from|away\s+from|dropped?)\s+([\w][\w\s\-\.]{2,35})",                  "USER_NAME", "switched_from"),
    # Tool/system relationships
    (r"([\w][\w\s\-\.]{2,25})\s+runs?\s+on\s+([\w][\w\s\-\.]{2,35})",                       None,        "runs_on"),
    (r"([\w][\w\s\-\.]{2,25})\s+(?:uses?|is\s+using)\s+([\w][\w\s\-\.]{2,35})",             None,        "uses"),
    (r"deploy(?:ing|ed)?\s+([\w][\w\s\-\.]{2,25})\s+(?:to|on)\s+([\w][\w\s\-\.]{2,25})",   None,        "deployed_to"),
    # Problems and fixes
    (r"([\w][\w\s\-\.]{2,30})\s+(?:is\s+)?(?:broken|failing|crashed|down|not\s+working)",   None,        "is_broken"),
    (r"(?:fixed?|resolved?|patched?)\s+(?:the\s+)?([\w][\w\s\-\.]{2,40})",                  "USER_NAME", "fixed"),
    # Requirements
    (r"([\w][\w\s]{2,25})\s+needs?\s+([\w][\w\s\-\.]{2,35})",                               None,        "needs"),
    # Ownership and creation
    (r"([\w][\w\s]{2,20})\s+owns?\s+([\w][\w\s]{2,35})",                                    None,        "owns"),
    (r"([\w][\w\s]{2,20})\s+(?:created?|made|built)\s+([\w][\w\s]{2,35})",                  "USER_NAME", "created"),
    # Usage context
    (r"using?\s+([\w][\w\s\-\.]{2,25})\s+for\s+([\w][\w\s\-\.]{2,35})",                    "USER_NAME", "uses_for"),
    # State
    (r"([\w][\w\s\-\.]{2,25})\s+(?:is|will be)\s+(?:the\s+)?([\w][\w\s\-\.]{2,35})",       None,        "is"),
]


def _build_patterns(user_name: str) -> list:
    """Replace USER_NAME placeholder with actual name."""
    result = []
    for pattern, default_subj, predicate in _PATTERNS_TEMPLATE:
        p = pattern.replace("USER_NAME", re.escape(user_name))
        d = default_subj.replace("USER_NAME", user_name) if default_subj else None
        result.append((p, d, predicate))
    return result


def _clean(s: str, max_len: int = 50) -> str:
    """Normalize whitespace and strip punctuation noise."""
    s = re.sub(r'\s+', ' ', s).strip().strip('"\'`.,;:()')
    return s[:max_len] if len(s) > max_len else s


# ── PARSERS ───────────────────────────────────────────────────────────────────

def _load_json_from_zip(zip_path: Path, filename: str) -> Optional[list]:
    """Extract and parse a JSON file from inside a zip archive."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = zf.namelist()
        # Exact match first
        if filename in names:
            with zf.open(filename) as f:
                return json.load(f)
        # Partial match (file may be in a subfolder)
        matches = [n for n in names if n.endswith(filename)]
        if matches:
            with zf.open(matches[0]) as f:
                return json.load(f)
        # Any JSON as fallback
        json_files = [n for n in names if n.endswith('.json')]
        if json_files:
            with zf.open(json_files[0]) as f:
                return json.load(f)
    return None


def parse_claude_export(source: Path) -> List[Dict]:
    """
    Parse Anthropic Claude export.
    Handles both zip archives and raw conversations.json files.
    Claude export format: list of conversations, each with chat_messages array.
    Each message has: sender ('human'|'assistant'), text, created_at.
    """
    if source.suffix == '.zip':
        data = _load_json_from_zip(source, 'conversations.json')
        if data is None:
            print(f"ERROR: Could not find conversations.json inside {source}")
            return []
    else:
        with open(source, 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)

    conversations = []
    for conv in data:
        if not isinstance(conv, dict):
            continue
        conv_data = {
            'uuid':       conv.get('uuid', 'unknown'),
            'name':       conv.get('name', '') or 'Untitled',
            'created_at': conv.get('created_at', ''),
            'turns':      []
        }
        for msg in conv.get('chat_messages', []):
            text = msg.get('text', '')
            # Claude sometimes nests content as list of blocks
            if not text and isinstance(msg.get('content'), list):
                text = ' '.join(
                    b.get('text', '') for b in msg['content']
                    if isinstance(b, dict) and b.get('type') == 'text'
                )
            if not text or len(text.strip()) < 10:
                continue
            if _NOISE_RE.match(text.strip()):
                continue
            conv_data['turns'].append({
                'role': 'human' if msg.get('sender') == 'human' else 'assistant',
                'text': text
            })
        if conv_data['turns']:
            conversations.append(conv_data)

    return conversations


def parse_chatgpt_export(source: Path) -> List[Dict]:
    """
    Parse OpenAI ChatGPT export.
    Handles both zip archives and raw conversations.json files.
    ChatGPT export format: list of conversations, each with a 'mapping' dict
    of node_id -> node objects. Each node has a 'message' with author.role
    and content.parts array.
    """
    if source.suffix == '.zip':
        data = _load_json_from_zip(source, 'conversations.json')
        if data is None:
            print(f"ERROR: Could not find conversations.json inside {source}")
            return []
    else:
        with open(source, 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)

    conversations = []
    for conv in data:
        if not isinstance(conv, dict):
            continue
        conv_data = {
            'uuid':       conv.get('id', 'unknown'),
            'name':       conv.get('title', '') or 'Untitled',
            'created_at': str(conv.get('create_time', '')),
            'turns':      []
        }
        mapping = conv.get('mapping', {})
        # Sort nodes by their position to preserve conversation order
        nodes = sorted(
            mapping.values(),
            key=lambda n: n.get('message', {}).get('create_time') or 0
        )
        for node in nodes:
            msg = node.get('message')
            if not msg:
                continue
            role = msg.get('author', {}).get('role', '')
            if role not in ('user', 'assistant'):
                continue
            content = msg.get('content', {})
            parts = content.get('parts', []) if isinstance(content, dict) else []
            text = ' '.join(str(p) for p in parts if isinstance(p, str) and p.strip())
            if not text or len(text.strip()) < 10:
                continue
            if _NOISE_RE.match(text.strip()):
                continue
            conv_data['turns'].append({
                'role': 'human' if role == 'user' else 'assistant',
                'text': text
            })
        if conv_data['turns']:
            conversations.append(conv_data)

    return conversations


def detect_format(source: Path) -> str:
    """Auto-detect export format from file contents."""
    try:
        if source.suffix == '.zip':
            with zipfile.ZipFile(source, 'r') as zf:
                names = zf.namelist()
                # ChatGPT zips typically include 'user.json' or 'message_feedback.json'
                if any('message_feedback' in n or 'user.json' in n for n in names):
                    return 'chatgpt'
                return 'claude'
        else:
            with open(source, 'r', encoding='utf-8', errors='replace') as f:
                sample = f.read(2000)
            # Claude exports have 'chat_messages', ChatGPT has 'mapping'
            if '"chat_messages"' in sample:
                return 'claude'
            if '"mapping"' in sample:
                return 'chatgpt'
    except Exception:
        pass
    return 'unknown'


# ── EXTRACTION ────────────────────────────────────────────────────────────────

def extract_triples(
    conversation: Dict,
    patterns: list,
    max_per_conv: int = 25
) -> List[Tuple[str, str, str]]:
    """
    Run regex patterns over all turns in a conversation.
    Returns list of (subject, predicate, object) triples.
    Deduplicates within the conversation.
    """
    facts = []
    seen = set()
    full_text = '\n'.join(t['text'] for t in conversation['turns'])
    sentences = re.split(r'(?<![.\d/\\A-Za-z])\.\s+', full_text)

    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 15 or len(sent) > 400:
            continue
        for pattern, default_subj, predicate in patterns:
            m = re.search(pattern, sent, re.IGNORECASE)
            if not m:
                continue
            groups = m.groups()
            if len(groups) == 1:
                subj = default_subj or _clean(conversation['name'].split()[0] if conversation['name'] else 'User')
                obj  = _clean(groups[0])
            else:
                subj = default_subj if default_subj else _clean(groups[0])
                obj  = _clean(groups[-1])

            if not subj or not obj or len(obj) < 3:
                continue
            key = f"{subj}|{predicate}|{obj}"
            if key not in seen:
                seen.add(key)
                facts.append((subj, predicate, obj))
            if len(facts) >= max_per_conv:
                return facts

    return facts


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Adam Framework — Extract facts from AI conversation history'
    )
    parser.add_argument('--source',     required=True,
                        help='Path to export zip or conversations.json')
    parser.add_argument('--vault-path', required=True,
                        help='Path to your Vault directory (e.g. C:/MyVault)')
    parser.add_argument('--format',     choices=['claude', 'chatgpt', 'auto'],
                        default='auto',
                        help='Export format (default: auto-detect)')
    parser.add_argument('--user-name',  default='User',
                        help='Your name as it appears in conversations (default: User)')
    parser.add_argument('--max-convos', type=int, default=500,
                        help='Max conversations to process (default: 500)')
    parser.add_argument('--max-per-conv', type=int, default=25,
                        help='Max facts per conversation (default: 25)')
    args = parser.parse_args()

    source     = Path(args.source)
    vault_path = Path(args.vault_path)
    imports_dir = vault_path / 'imports'
    imports_dir.mkdir(parents=True, exist_ok=True)
    output_path = imports_dir / 'extracted_triples.json'
    report_path = imports_dir / 'extraction_report.txt'

    if not source.exists():
        print(f"ERROR: Source file not found: {source}")
        sys.exit(1)

    # Detect format
    fmt = args.format
    if fmt == 'auto':
        fmt = detect_format(source)
        if fmt == 'unknown':
            print("ERROR: Could not auto-detect format. Use --format claude or --format chatgpt")
            sys.exit(1)
        print(f"Detected format: {fmt}")

    # Parse
    print(f"Parsing {source.name}...")
    if fmt == 'claude':
        conversations = parse_claude_export(source)
    else:
        conversations = parse_chatgpt_export(source)

    if not conversations:
        print("ERROR: No conversations found. Check the file format.")
        sys.exit(1)

    print(f"Found {len(conversations)} conversations with content")

    # Build patterns with user's name
    patterns = _build_patterns(args.user_name)

    # Extract
    to_process = conversations[:args.max_convos]
    all_facts = []
    conv_stats = []
    seen_global = set()

    for i, conv in enumerate(to_process):
        facts = extract_triples(conv, patterns, args.max_per_conv)
        # Global dedup across conversations
        new_facts = []
        for f in facts:
            key = f"{f[0]}|{f[1]}|{f[2]}"
            if key not in seen_global:
                seen_global.add(key)
                new_facts.append(f)
        if new_facts:
            all_facts.extend(new_facts)
            conv_stats.append({
                'name':       conv['name'],
                'uuid':       conv['uuid'],
                'created_at': conv['created_at'],
                'facts':      len(new_facts)
            })
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(to_process)} conversations "
                  f"({len(all_facts)} facts so far)...")

    # Write output
    output = {
        '_meta': {
            'generated':        datetime.now().isoformat(),
            'source':           str(source),
            'format':           fmt,
            'user_name':        args.user_name,
            'total_convos_in_export': len(conversations),
            'convos_processed': len(to_process),
            'convos_with_facts': len(conv_stats),
            'total_facts':      len(all_facts),
            'next_step':        'Run ingest_triples.ps1 to load these into your neural graph'
        },
        'facts': all_facts,
        'conversation_stats': conv_stats
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Write human-readable report
    report_lines = [
        "Adam Framework — Legacy Import Extraction Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 55,
        f"Source:              {source.name}",
        f"Format:              {fmt}",
        f"User name used:      {args.user_name}",
        "",
        f"Conversations in export:   {len(conversations)}",
        f"Conversations processed:   {len(to_process)}",
        f"Conversations with facts:  {len(conv_stats)}",
        f"Total facts extracted:     {len(all_facts)}",
        "",
        "── NEXT STEP ──────────────────────────────────────",
        f"1. Review: {output_path}",
        "   Open it and check that the facts look reasonable.",
        "   The file is plain JSON — you can edit or remove",
        "   any entries before ingesting.",
        "",
        "2. Ingest: Run ingest_triples.ps1",
        "   This will load all facts into your neural graph.",
        f"   Estimated time: ~{max(1, len(all_facts) // 13)} minutes",
        "",
        "── TOP CONVERSATIONS BY FACTS ─────────────────────",
    ]
    top = sorted(conv_stats, key=lambda x: -x['facts'])[:15]
    for c in top:
        report_lines.append(f"  [{c['facts']:>3} facts] {c['name'][:60]}")

    report_lines += [
        "",
        "── SAMPLE FACTS (first 20) ────────────────────────",
    ]
    for f in all_facts[:20]:
        report_lines.append(f"  {f[0]} | {f[1]} | {f[2]}")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"\n{'=' * 55}")
    print(f"Extraction complete.")
    print(f"  Facts extracted:  {len(all_facts)}")
    print(f"  Output:           {output_path}")
    print(f"  Report:           {report_path}")
    print(f"\nReview the output file, then run ingest_triples.ps1")
    print(f"Estimated ingest time: ~{max(1, len(all_facts) // 13)} minutes")


if __name__ == '__main__':
    main()
