---
name: Bug Report
about: Something broke. Help us fix it.
labels: bug
---

## What broke

<!-- One sentence: what went wrong? -->

## Which component

- [ ] SENTINEL (boot / watchdog)
- [ ] Neural graph / mcporter / nmem
- [ ] reconcile_memory.py (sleep cycle)
- [ ] legacy_importer.py (Session 000 extraction)
- [ ] ingest_triples.ps1 (Session 000 ingest)
- [ ] openclaw.json config
- [ ] Something else

## Steps to reproduce

1.
2.
3.

## What you expected

<!-- What should have happened? -->

## What actually happened

<!-- Paste the exact error message or log output. -->

```
paste error / log here
```

## Your setup

- OS: <!-- Windows 10 / 11 -->
- Python version: <!-- python --version -->
- OpenClaw version: <!-- check openclaw --version or your install -->
- Model / provider: <!-- e.g. NVIDIA Kimi K2.5, OpenRouter, Ollama -->
- Neural memory installed: <!-- yes / no -->

## Relevant log output

<!-- Check these files and paste anything relevant: -->
<!-- %USERPROFILE%\.openclaw\sentinel.log -->
<!-- <VAULT>\imports\ingest_log.txt -->
<!-- <VAULT>\workspace\memory\_reconcile_state.json -->

```
paste logs here
```

## Already checked LESSONS_LEARNED.md?

- [ ] Yes — not listed there
- [ ] No — checking now
