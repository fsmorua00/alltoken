# alltoken

**One Claude Code plugin that aggregates the best token-saving techniques in a
single place.** No more hunting through a dozen scattered tools — it's all here:
context auditing, output modes (including **Caveman**, where Claude answers in
grunt-short prose), minimum-viable-model routing, local usage analytics, and
deterministic output compression.

> Philosophy: **real gains at low risk, with no inflated savings numbers.**
> Proven techniques are ready to use. Experimental/gimmicky ones are included
> but **opt-in**, with the honest warnings they deserve — never applied behind
> your back.

🇧🇷 [Leia em Português](README.pt-BR.md)

---

## The idea

`compute spent ≈ tokens processed × model used`. Every technique here moves one
of those variables — either **input** tokens (context), **output** tokens
(responses), or the **model**. The plugin attacks all three fronts:

| Front | Tool | How |
|---|---|---|
| **Input / context** | `/token-audit`, `/token-optimize` | Measures the "context floor" and trims CLAUDE.md, MCPs, and skills |
| **Output / responses** | **Caveman · Telegraphic · Concise** modes | Change how Claude writes so every reply costs less |
| **Model / compute** | `minimum-viable-model` skill, `token-auditor` agent | Route grunt work to Haiku, save the frontier model for judgment |
| **Input / logs** | `scripts/compress_output.py` | Compresses verbose command output before Claude reads it |

See the full menu anytime with **`/tokens`**.

---

## The magic: `/alltoken` ✨

Installed the plugin? **One command applies everything, in any project:**

```
/alltoken             # applies everything + activates Concise mode
/alltoken caveman     # same, but Claude talks caveman 🦴
```

What happens in a single shot:

1. **Audits** the project's context floor (before/after).
2. **Installs and activates** the output modes (Caveman/Telegraphic/Concise)
   via the `outputStyle` key in the project settings.
3. **Injects Anthropic's official guidance** as a lean "token discipline" block
   in CLAUDE.md — concision, context hygiene, minimum-viable-model routing,
   scripts over re-prompting. Since CLAUDE.md loads on every session, **every
   future session in the project follows the official best practices
   automatically**.
4. **Proposes** trimming CLAUDE.md if it's over the ~200-line guideline
   (showing the diff) and lists what needs a human decision (e.g. MCPs).

The block is **idempotent**: re-running `/alltoken` updates it instead of
duplicating. Revert anytime: `/output-style default` + `git checkout`. The
distilled official guidance lives in
[`docs/official-best-practices.md`](docs/official-best-practices.md).

---

## Installation

### As a plugin (recommended)

```
/plugin marketplace add fsmorua00/alltoken
/plugin install alltoken@alltoken-marketplace
```

### Scripts only (no plugin)

```bash
python3 scripts/audit.py --root .                              # audit
some-cmd 2>&1 | python3 scripts/compress_output.py --stats     # compression
python3 scripts/install_styles.py                              # install output modes
```

---

## The tools

### 1. Audit and optimize context (proven)

```
/token-audit       # measures the context floor and ranks the waste
/token-optimize    # applies the safe fixes, showing each diff
```

The engine (`scripts/audit.py`) is **deterministic** — no AI, no network. It
reports CLAUDE.md size, configured MCP servers, and skill descriptions, with
~4-chars/token estimates (labelled as estimates, never marketing numbers).

### 2. Output modes — incl. Caveman 🦴 (proven)

The cheapest way to cut **output** tokens is changing how Claude writes.
Three modes, from most radical to professional:

| Mode | Voice | Use |
|---|---|---|
| **Caveman** | "Fix function. Handle empty list. Done." | Max savings, informal |
| **Telegraphic** | Clipped but grammatical telegram English | Middle ground |
| **Concise** | Professional, zero fluff | Serious work |

**In every mode, code, commands, paths, and numbers stay exact** — caveman
style applies to prose only, never to anything that must be correct.

Install and activate:

```bash
python3 scripts/install_styles.py     # copies styles to .claude/output-styles/
```
```
/output-style caveman      # activate (or telegraphic / concise)
/output-style default      # back to normal
```

### 3. Minimum viable model (proven)

The `minimum-viable-model` skill guides Claude to run grunt work (scraping,
formatting, summarizing, extraction) on the cheapest model that does the job,
reserving the frontier model for genuine judgment. The `token-auditor`
subagent already runs on `haiku` — it leads by example.

### 4. Output compression (proven)

```bash
npm test 2>&1 | python3 scripts/compress_output.py --stats
# [alltoken] 3120 → 84 lines, ~94% fewer chars
```

Deterministic rules: collapses duplicates, strips boilerplate (download bars,
funding notices, ANSI codes), middle-truncates, and **always** preserves
error/warning lines. It's lossy — for logs you'd only skim. Savings depend on
how noisy the input is (clean build ≈ nothing; huge log ≈ 80–95%).

### 5. Measure reality: `/token-usage` (proven)

Inspired by [ccusage](https://github.com/ryoppippi/ccusage) (~16k ⭐): reads
Claude Code's own local logs (`~/.claude/projects`, nothing leaves your
machine) and shows **where your tokens actually went** — by model, output
share, cache-read ratio — then maps each signal to the toolbox technique that
fixes it. Zero dependencies. For full cost reports, use ccusage itself.

### 6. Ecosystem radar

We analyzed the most-starred Claude Code projects on GitHub and mapped them in
[`docs/ecosystem.md`](docs/ecosystem.md): what we **absorbed** (re-implemented,
dependency-free), what we **recommend as companions**
([Serena](https://github.com/oraios/serena) ~19k ⭐ for symbol-level semantic
reads, ccusage for costs,
[claude-code-router](https://github.com/musistudio/claude-code-router) for
engine swapping) and what we deliberately did **not** absorb — heavy frameworks
pay context rent on every session. The bar: a technique must save more than it
costs to have installed.

### 7. Experimental — opt-in, with tradeoffs ⚠️

Included for completeness, **never applied automatically**:

- **Text-as-image** (`scripts/text_to_image.py`) — renders text as a PNG.
  Lossy (OCR misreads), savings not guaranteed, **never** for code. Needs Pillow.
- **Engine swap** (`docs/engine-swap.md`) — pointing Claude Code at GLM/
  DeepSeek via environment variables. Trades quality and (DeepSeek) privacy.

---

## Structure

```
.claude-plugin/{plugin,marketplace}.json   # manifest + installable as a marketplace
commands/
  alltoken.md             # /alltoken — the magic: applies everything in one shot
  tokens.md               # /tokens — index of everything
  token-audit.md          # /token-audit
  token-optimize.md       # /token-optimize
  token-usage.md          # /token-usage — local log analytics
agents/token-auditor.md   # review subagent (haiku)
skills/minimum-viable-model/SKILL.md
output-styles/            # caveman.md · telegraphic.md · concise.md
hooks/hooks.json          # SessionStart nudge (1 line, only when waste is high)
scripts/
  apply_all.py            # /alltoken engine (one-shot, idempotent)
  usage_stats.py          # usage analytics (ccusage-inspired, no deps)
  audit.py                # deterministic audit engine
  compress_output.py      # output compressor
  install_styles.py       # installs the output modes
  text_to_image.py        # experimental (opt-in)
  session_start.py        # nudge hook
docs/
  official-best-practices.md  # Anthropic's official guidance, distilled
  ecosystem.md                # radar of the ecosystem's top libraries
  engine-swap.md              # experimental (opt-in)
```

---

## License

MIT — see [LICENSE](LICENSE).
