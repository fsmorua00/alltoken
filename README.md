# tokenwise

**Um plugin para o Claude Code que audita a lógica dos seus projetos e aplica
otimizações de token de forma automática e segura** — do básico (forçar respostas
concisas) ao avançado (higiene de contexto, roteamento por modelo mínimo viável,
compressão de output).

> Filosofia: **ganho real com risco baixo, sem números de economia inflados.**
> As técnicas comprovadas ficam ligadas por padrão. As experimentais/gimmicky
> ficam documentadas como opt-in, com os avisos honestos que elas merecem.

*(English summary at the bottom.)*

---

## O que ele faz

`compute gasto ≈ tokens processados × modelo usado`. Toda otimização aqui mexe
numa dessas duas variáveis. O plugin ataca as duas:

| Componente | O que faz | Custo/risco |
|---|---|---|
| **`/token-audit`** | Roda uma análise **determinística** (sem IA) do "piso de contexto": tamanho do CLAUDE.md, MCPs configurados, descrições de skills — e soma um diagnóstico com julgamento (trabalho que devia ser script, uso do modelo forte pra tarefa braçal). | Nenhum |
| **`/token-optimize`** | Aplica só as correções **seguras** (respostas concisas, enxugar CLAUDE.md, apertar descrições de skills), mostrando o diff antes de cada mudança. | Baixo, reversível via git |
| **Agente `token-auditor`** | Subagente rodando em `haiku` que revisa a lógica do projeto focado só em desperdício de token. | Baixo |
| **Skill `minimum-viable-model`** | Guia para escolher o modelo mais barato que resolve cada tarefa. | Nenhum |
| **Hook SessionStart** | Injeta **uma linha** de aviso apenas se houver desperdício alto. Silencioso quando o projeto já está enxuto. | ~mínimo |
| **`scripts/compress_output.py`** | Comprime output verboso de comandos (logs, install, testes) antes do Claude ler, com regras determinísticas. | Baixo (lossy por design) |

---

## Instalação

### Como plugin (recomendado)

```bash
# Adicione este repositório como marketplace
/plugin marketplace add fsmoura00/Claude

# Instale o plugin
/plugin install tokenwise@tokenwise-marketplace
```

Depois disso os comandos `/token-audit` e `/token-optimize`, o agente e a skill
ficam disponíveis em qualquer sessão.

### Só os scripts (sem plugin)

Os scripts em `scripts/` funcionam soltos, sem nada instalado:

```bash
python3 scripts/audit.py --root .            # auditoria legível
python3 scripts/audit.py --root . --json     # saída pra automação
some-noisy-command 2>&1 | python3 scripts/compress_output.py --stats
```

---

## Uso

### Auditar

```
/token-audit
```

Exemplo do que o motor determinístico reporta:

```
════════════════════════════════════════════════════════════════
  tokenwise audit
  project: /home/você/seu-projeto
════════════════════════════════════════════════════════════════

  Estimated context floor: ~6,420 tokens loaded before your first message.
  Addressable waste (high+medium): ~3,900 tokens/session.

  Findings (most impactful first):
  🔴 [CLAUDE.md] (~2100 tok) CLAUDE.md is 480 lines / ~4600 tokens — over the
       200-line guideline. This is re-injected context on every turn.
       ↳ fix: Trim to a lean directory of project conventions...
  🟡 [MCP] (~2100 tok) 3 MCP server(s) configured...
  🔵 [output] No concise-output convention detected.
```

### Otimizar

```
/token-optimize          # mostra cada diff e pede confirmação
/token-optimize --yes    # aplica os fixes seguros sem perguntar
```

Ele **nunca** apaga informação em silêncio — ao enxugar o CLAUDE.md, o conteúdo
longo é movido para arquivos e o local é informado. Tudo fica no git, fácil de reverter.

### Comprimir output pesado

```bash
npm test 2>&1 | python3 scripts/compress_output.py --stats
# [tokenwise] 3120 → 84 lines, ~94% fewer chars (2900 collapsed, 136 trimmed)
```

Regras determinísticas: colapsa linhas idênticas, remove boilerplate (barras de
download, avisos de funding, códigos ANSI), trunca pelo meio preservando head+tail,
e **sempre** mantém linhas que parecem erro/warning/falha.

**Expectativa honesta:** a economia depende 100% de quão barulhento é o input.
Build limpo economiza quase nada; log de install de 5.000 linhas encolhe 80–95%.
É lossy — use para logs que você só passaria o olho, não para output que precisa ler palavra por palavra.

---

## O que é comprovado vs. experimental

**Ligado por padrão (ganho real, risco baixo):**
- Higiene de contexto (auditoria do piso, enxugar CLAUDE.md, revisar MCPs/skills)
- Respostas concisas
- Modelo mínimo viável (grunt work no modelo barato)
- Compressão determinística de output

**Deliberadamente NÃO incluído** (o vídeo que inspirou isto os promove, mas são
gimmicky ou arriscados; documentados aqui só para transparência):
- **Texto-como-imagem** para economizar tokens — OCR é lossy, tokens de imagem
  não são garantidamente mais baratos, e pode ser "corrigido" a qualquer momento.
- **Trocar o engine** para GLM/DeepSeek via variáveis de ambiente — funciona, mas
  troca qualidade e (DeepSeek) levanta questões de privacidade. É decisão sua, não do plugin.
- **Rodar modelo local** — impraticável para qualidade de ponta em hardware de consumidor hoje.

Se você quiser explorar essas mesmo assim, a skill `minimum-viable-model` e a
documentação te dão o contexto — mas o plugin não vai aplicá-las por baixo dos panos.

---

## Estrutura

```
.claude-plugin/
  plugin.json          # manifesto do plugin
  marketplace.json     # torna o repo instalável como marketplace
commands/
  token-audit.md       # /token-audit
  token-optimize.md    # /token-optimize
agents/
  token-auditor.md     # subagente de revisão (haiku)
skills/
  minimum-viable-model/SKILL.md
hooks/
  hooks.json           # SessionStart nudge
scripts/
  audit.py             # motor de auditoria determinístico (núcleo)
  compress_output.py   # compressor de output
  session_start.py     # hook de aviso de uma linha
```

---

## English

**tokenwise** is a Claude Code plugin that audits your project's logic for token
waste and applies safe, automatic optimizations — from concise output to context
hygiene and minimum-viable-model routing. Proven techniques are on by default;
gimmicky/risky ones (text-as-image, engine swapping, local models) are documented
but intentionally *not* applied for you. Install with
`/plugin marketplace add fsmoura00/Claude` then `/plugin install tokenwise@tokenwise-marketplace`,
or run the scripts standalone. Token counts are ~4-chars/token estimates, never
inflated marketing numbers.

## License

MIT — see [LICENSE](LICENSE).
