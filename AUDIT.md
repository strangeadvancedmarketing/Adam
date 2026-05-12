# Adam Framework — Model Compatibility Audit

**Date:** 2026-03-20  
**Status:** CRITICAL — Multiple model-dependent components identified  
**Action Required:** Yes — before marketing as "works with any model"

---

## Executive Summary

The Adam Framework claims to work with any LLM model, but **multiple components have hard assumptions that only work with specific models**. A user installing this with DeepSeek, Llama, Mistral, or other models will encounter silent failures or broken behavior.

### Components With Model Dependencies

| Component | Location | Issue | Severity |
|-----------|----------|-------|----------|
| Coherence Monitor | `tools/coherence_monitor.py` | Detects `<scratchpad>` tags — only works if model follows that instruction | **CRITICAL** |
| AGENTS.md ReAct Loop | Vault `AGENTS.md` | Instructs model to use `<scratchpad>` blocks — model-specific compliance | **CRITICAL** |
| Token Context Window | `coherence_monitor.py` | Hardcoded `CONTEXT_WINDOW = 131072` (Kimi K2.5) | **HIGH** |
| Behavioral Constitution | Live `AGENTS.md` | 382-line cognitive framework assumes agentic model compliance | **HIGH** |
| Documentation Claims | README.md, ARCHITECTURE.md | "swap the LLM — the Vault survives" — true for files, NOT for coherence | **MEDIUM** |

---

## Detailed Findings

### 1. Coherence Monitor — Scratchpad Detection (CRITICAL)

**File:** `tools/coherence_monitor.py`

**Problem:** The Layer 5 coherence monitor's primary drift signal is detecting whether the model outputs `<scratchpad>` tags. This is NOT a universal LLM behavior — it's an instruction in AGENTS.md that models may or may not follow.

**Evidence:**
- Kimi K2.5: Reliably outputs `<scratchpad>` tags (trained for agentic compliance)
- DeepSeek V3.1: Does NOT output scratchpad tags in normal mode
- DeepSeek V3.1: When it DOES output them, it regurgitates the entire instruction block verbatim (worse than not outputting)
- Claude: Would need explicit instruction (high compliance expected)
- Llama, Mistral, etc.: Unknown compliance — likely low

**Impact:**
- **Without scratchpad tags:** Monitor always scores `scratchpad_fired: false` → drift score 0.6 → re-anchor triggers every 5 minutes → BOOT_CONTEXT.md balloons → gateway crashes
- **With regurgitated tags:** Model dumps internal instructions to user, wastes tokens, provides no actual reasoning

**Status:** FIX DEPLOYED (2026-03-20)  
Coherence monitor v2.0.0 removes scratchpad detection entirely, uses token depth only.  
This is a STOP-GAP, not a complete solution.

---

### 2. AGENTS.md ReAct Loop (CRITICAL)

**File:** `vault-templates/AGENTS.md` (template) and live Vault copies

**Problem:** The entire 382-line AGENTS.md file is written assuming the model will:
1. Execute a multi-step ReAct cognitive loop
2. Output that reasoning in `<scratchpad>` blocks
3. Follow detailed structured instructions about speculation, shadow simulation, etc.

**Model Compliance Reality:**
- **Kimi K2.5:** High compliance (specifically trained for agentic tool use)
- **Claude (Sonnet/Opus):** High compliance (strong instruction following, trained on XML)
- **DeepSeek V3.1 (chat mode):** LOW compliance — ignores scratchpad instruction OR regurgitates it
- **DeepSeek R1 (thinking mode):** Uses `<think>` tags, not `<scratchpad>`
- **Llama 3.3 70B:** Moderate compliance (depends on system prompt position)
- **GPT-4o:** Moderate compliance (prefers natural language)
- **Mistral, Qwen, etc.:** Unknown

**Impact:**
- Models that don't follow AGENTS.md have no cognitive framework
- The "Mercy Step" speculation, shadow simulation, and foundation checks never fire
- The agent becomes a basic chatbot with file access — not the identity-sovereign AI advertised

---

### 3. Hardcoded Context Window (HIGH)

**File:** `tools/coherence_monitor.py`

```python
CONTEXT_WINDOW = 131072   # Kimi K2.5
```

**Problem:** Context window is hardcoded to Kimi K2.5's 131K tokens. Other models:
- DeepSeek V3.1: 200K tokens
- Claude 3.5: 200K tokens
- GPT-4 Turbo: 128K tokens
- Llama 3.3 70B: 128K tokens

**Impact:**
- With DeepSeek V3.1 (200K), the monitor thinks context is at 65.5% when it's actually at 43%
- Triggers re-anchors too early (wastes resources) or too late (misses real drift)
- Percentages in logs are wrong

**Fix Required:** Read context window from model config or make it configurable

---

### 4. Documentation Claims (MEDIUM)

**Files:** README.md, ARCHITECTURE.md

**Claims made:**
> "The memory is in the files. The model is just the reader — swap the LLM, keep the Vault, your AI's continuity persists."

> "Swap the LLM — the Vault survives."

**Reality:**
- **TRUE for Layers 1-4:** File-based memory, neural graph, reconciliation are model-agnostic
- **FALSE for Layer 5:** Coherence monitoring has model-specific assumptions
- **FALSE for behavioral constitution:** AGENTS.md compliance varies by model

**Required documentation updates:**
1. Add "Model Compatibility" section to README
2. List tested models with compatibility notes
3. Remove or qualify "works with any model" claims
4. Add setup guidance for non-Kimi models

---

## Components That ARE Model-Agnostic ✓

These components correctly make no model assumptions:

| Component | Why It Works |
|-----------|--------------|
| Vault file structure | Plain Markdown — any model can read/write |
| SOUL.md, CORE_MEMORY.md | Identity files work regardless of model |
| Neural graph (nmem) | SQLite + spreading activation — model-independent |
| reconcile_memory.py | Uses Gemini explicitly — designed as a separate service |
| SENTINEL watchdog | Process management — no model awareness needed |
| Memory search | OpenClaw handles hybrid search — model-transparent |
| memoryFlush | Triggered by token threshold, writes files — model-agnostic |

---

## Recommended Fixes

### Immediate (Before Next Release)

> **v2.0 deployed** — scratchpad detection removed, token-depth monitoring is now the sole signal.
> coherence_monitor.py v2.0.0 is model-agnostic; no behavioral tag compliance required.

1. **✅ DONE:** Remove scratchpad detection from coherence_monitor.py
2. **TODO:** Make CONTEXT_WINDOW configurable per model
3. **TODO:** Add model compatibility section to README
4. **TODO:** Document tested models and their quirks

### Short-Term (v1.3)

5. **TODO:** Create model-specific AGENTS.md variants:
   - `AGENTS.kimi.md` — Full ReAct with scratchpad
   - `AGENTS.claude.md` — Uses `<thinking>` tags
   - `AGENTS.deepseek.md` — Simplified, no custom tags
   - `AGENTS.generic.md` — Minimal, works with any model

6. **TODO:** Add model detection to SENTINEL:
   - Read model ID from openclaw.json
   - Select appropriate AGENTS.md variant at boot
   - Log which variant is active

7. **TODO:** Update Layer 5 to be model-aware:
   ```python
   if "kimi" in model_id:
       look_for("<scratchpad>")
   elif "claude" in model_id:
       look_for("<thinking>")  # or Claude's native format
   elif "deepseek" in model_id and thinking_mode:
       look_for("<think>")
   else:
       skip_behavioral_detection()  # token-depth only
   ```

### Long-Term (v2.0)

8. **Consider:** Model capability registry:
   - JSON file defining each model's capabilities
   - Context window, tag compliance, thinking mode support
   - Auto-loaded at session start

9. **Consider:** Behavioral constitution abstraction:
   - Core principles that work everywhere
   - Model-specific enhancements as optional layers

---

## Testing Matrix

Before claiming "works with any model," test with:

| Model | Provider | Context | Status |
|-------|----------|---------|--------|
| Kimi K2.5 | NVIDIA | 131K | ✅ Production validated |
| DeepSeek V3.1 | NVIDIA | 200K | ⚠️ Working after fix, no scratchpad |
| Claude Sonnet | Anthropic | 200K | ❓ Not tested |
| Claude Opus | Anthropic | 200K | ❓ Not tested |
| Llama 3.3 70B | NVIDIA | 128K | ⚠️ Poor behavioral compliance |
| GPT-4 Turbo | OpenAI | 128K | ❓ Not tested |
| Mistral Large | Mistral | 128K | ❓ Not tested |
| Qwen 2.5 | Local | 32K | ❓ Not tested |

---

## Conclusion

The Adam Framework's file-based architecture IS genuinely model-agnostic for persistence and memory. However, the behavioral layer (AGENTS.md) and coherence monitoring (Layer 5) have significant model-specific assumptions that will cause problems for users on non-Kimi models.

**Until these are fixed, honest marketing language should be:**

> "The Adam Framework's memory and identity files work with any LLM. The full coherence monitoring and cognitive framework have been validated with Kimi K2.5 and may require adjustment for other models."

---

*Audit conducted by Claude (via Claude.ai) during debugging session with Jereme Strange*
