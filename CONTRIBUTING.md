# Contributing to the Adam Framework

Thanks for being here. This framework was built by one person solving a real problem — and it'll get better with people who are actually using it.

---

## What's Most Useful Right Now

### 1. Share Your Build
The most valuable thing you can do is tell us what you built and what you ran into. Open a Discussion → **Show Your Build** and drop:
- What model/setup you're using
- What broke or confused you
- What's working well

### 2. Bug Reports
If something breaks, open an Issue. Include:
- Which phase (Identity / Neural Memory / Session 000 / Sleep Cycle)
- Your OS and Python version
- The exact error message and what you were running

### 3. Pull Requests Welcome
Especially for:
- **Linux/macOS port of SENTINEL** — it's the biggest gap. If you can write a bash equivalent, that unlocks the framework for everyone not on Windows
- **Fixes to the setup guides** — if a step confused you, a clearer explanation is a contribution
- **Tool additions** — additional reconcile/ingest patterns, alternative TTS configs, model-specific configs

### 4. What's Not a Good PR Right Now
- Major architectural changes without prior discussion — open an Issue first
- New dependencies without strong justification — the framework is intentionally lean

---

## How to Submit a PR

```bash
git clone https://github.com/strangeadvancedmarketing/adam
cd adam
git checkout -b your-feature-name
# make your changes
git commit -m "clear description of what this does"
git push origin your-feature-name
```

Then open a PR. Describe what it does and why.

---

## Philosophy

The Adam Framework is built around one principle: **the memory is in the files, not the model.** Contributions should respect that — keeping the architecture auditable, model-agnostic, and operator-controlled.

No cloud dependencies. No vendor lock-in. No magic.

---

## Questions?

Open a Discussion. That's what they're for.
