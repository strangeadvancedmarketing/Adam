# Contributing to the Adam Framework

Thanks for being here. This project was built by one non-coder who needed something
to work and kept fixing it until it did. Contributions that come from the same place
— real use, real problems, real fixes — are what this repo is built for.

---

## What's Most Needed Right Now

### High Priority
- **Linux / macOS port of SENTINEL** — `SENTINEL.template.ps1` is PowerShell-only.
  A bash equivalent that covers the same boot sequence (date injection, sleep cycle,
  BOOT_CONTEXT compilation, gateway launch, watchdog loop) would open this framework
  to the majority of developers. This is the single highest-value contribution.

- **Model provider templates** — `openclaw.template.json` is currently wired for NVIDIA.
  Templates or documented config blocks for OpenRouter, Groq, Ollama, and Anthropic
  would make setup faster for people on different providers.

### Medium Priority
- **`neural_metrics.json` visualizer** — the sleep cycle now snapshots neuron/synapse
  counts after every run. A simple chart in `showcase/` that reads that file and
  plots growth over time would make the "live growing system" story visible.

- **Test coverage for `reconcile_memory.py`** — the reconcile script has solid error
  handling but no tests. Basic pytest coverage for the state management, validation,
  and backup logic would make it safer to iterate on.

- **`legacy_importer.py` support for additional export formats** — currently handles
  Claude and ChatGPT exports. Gemini, Perplexity, and Character.ai exports would
  broaden the Session 000 seeding story considerably.

---

## How to Contribute

1. **Fork the repo** and create a branch from `master`
2. **Make your change** — keep it focused, one thing per PR
3. **Test it on a real system** — this is a production framework, not a demo.
   If your change touches SENTINEL or reconcile_memory.py, run it.
4. **Update the relevant doc** — if you change behavior, update the doc that describes it.
   If you add a new pattern, add a LESSONS_LEARNED entry if it has a failure mode.
5. **Open a PR** with a clear description of what changed and why

---

## What a Good PR Looks Like

**Good:**
- "Here's a bash port of SENTINEL — tested on Ubuntu 22.04 and macOS Sonoma"
- "Fixed reconcile_memory.py crash when CORE_MEMORY.md has a BOM character"
- "Added Ollama config block to openclaw.template.json with tested settings"

**Not a good fit:**
- Rewrites that change the core architecture without prior discussion
- Changes that add cloud dependencies to a framework designed to run locally
- Documentation-only PRs that haven't been verified against the actual system behavior

---

## Repo Philosophy

A few things that matter here:

**Local first.** Every component runs on the operator's machine. Contributions that
introduce cloud dependencies, phone-home behavior, or vendor lock-in will be declined.

**Files are the memory.** The Vault architecture — human-readable Markdown files that
the AI reads — is the foundation. Contributions that work with that model are welcome.
Contributions that try to replace it with a database or proprietary format are not.

**Accuracy over polish.** The LESSONS_LEARNED and PROOF docs exist because real failures
happened. If your contribution fixes something that was broken, document the failure mode.
A repo that tells the truth about what broke and why is more valuable than one that looks
clean but hides its scars.

**One person can build this.** The whole point of the project is that a non-developer
running a small business built a production AI memory system with consumer hardware and
free APIs. Contributions that lower the bar for the next person — clearer docs, simpler
setup, better error messages — are exactly right.

---

## Questions

Open an issue. If it's a quick question, the issue is fine. If it's a bigger discussion
about architecture or direction, tag it `discussion` and lay out your thinking.
