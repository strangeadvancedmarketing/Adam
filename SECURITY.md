# Security Policy

## Supported Versions

The Adam Framework is a local deployment architecture. There is no hosted service,
no cloud backend, and no user data transmitted anywhere except to the LLM API provider
you configure (NVIDIA, OpenRouter, etc.).

| Component | Supported |
|-----------|-----------|
| Latest release on `master` | ✅ |
| Older releases | No backports — update to latest |

---

## What To Report

Security issues relevant to this framework include:

- **Template files** (`engine/SENTINEL.template.ps1`, `engine/openclaw.template.json`)
  that could expose secrets if copied without proper placeholder substitution
- **Tools** (`reconcile_memory.py`, `coherence_monitor.py`, `legacy_importer.py`)
  that handle file paths or user data in unsafe ways
- **Documentation** that gives instructions which could result in credentials being
  committed to version control or exposed in logs

## What Is Out Of Scope

- Vulnerabilities in OpenClaw itself — report those to the OpenClaw project
- Vulnerabilities in neural_memory, mcporter, or other dependencies — report to their maintainers
- Issues with the LLM API providers you connect (NVIDIA, OpenRouter, etc.)

---

## Reporting a Vulnerability

Open a **private security advisory** via GitHub:
[Report a vulnerability](https://github.com/strangeadvancedmarketing/Adam/security/advisories/new)

Include:
- What file or component is affected
- How it could be exploited
- A suggested fix if you have one

We'll respond within 7 days.

---

## Security Notes for Deployers

1. **Never commit your live `SENTINEL.ps1` or `openclaw.json`** — they contain API keys
   and personal Vault paths. The `.gitignore` blocks them by default. Do not override this.

2. **Your Vault path contains personal memory files** — do not make your Vault directory
   publicly accessible or sync it to a public repo.

3. **API keys in `openclaw.json`** belong in the `env` block. Do not hardcode them in
   scripts or templates you share.

4. **The legacy importer reads your full conversation history** — run it locally only,
   never pipe your export zip through an untrusted environment.
