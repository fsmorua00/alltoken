# Engine swap (EXPERIMENTAL / opt-in)

Claude Code is a *harness*; the model behind it can be pointed at other providers
via environment variables. Some providers price compute differently and can give
you more capacity per dollar for routine work. This is a **your-call** technique —
tokenwise documents it but never flips it for you.

## Honest tradeoffs

- **Quality drops.** Non-frontier / third-party models are weaker at hard
  reasoning, refactors, and subtle correctness. Keep frontier for those.
- **Privacy.** Some providers (e.g. DeepSeek) run on infrastructure with different
  data-handling than Anthropic. Don't route sensitive code through them.
- **Compatibility.** Third-party endpoints emulate the API to varying degrees;
  tool use, streaming, and long context may behave differently.
- **Offers change.** Provider plans and prices shift constantly — verify current
  terms yourself before committing.

## How the switch works

Claude Code reads a small set of environment variables to decide which endpoint
and model to talk to. The exact variable names and support depend on your Claude
Code version — check `claude --help` and the official docs for the current set
before relying on any of these. Conceptually you point it at:

```bash
# Illustrative only — confirm the current variable names in the official docs.
export ANTHROPIC_BASE_URL="https://<provider-endpoint>"
export ANTHROPIC_AUTH_TOKEN="<your-provider-key>"
export ANTHROPIC_MODEL="<provider-model-id>"
```

Providers people commonly evaluate for cost-per-dollar include **Z.ai's GLM**
plans and **DeepSeek** plans. Treat any capacity claims skeptically and measure
on your own workload.

## The tokenwise recommendation

Prefer the **minimum-viable-model** approach *inside* the Anthropic ecosystem
first (route grunt work to Haiku via the `minimum-viable-model` skill). It gets
you most of the savings with none of the quality/privacy tradeoffs. Reach for a
full engine swap only if you've measured that in-ecosystem routing isn't enough.
