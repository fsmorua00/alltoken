# tokenwise

**Um único plugin para o Claude Code que agrega as melhores técnicas de economia
de token num só lugar.** Nada de espalhar dez ferramentas soltas — aqui está tudo:
auditoria de contexto, modos de saída (incluindo o **Caveman**, o Claude falando
como neandertal pra cortar tokens), roteamento por modelo mínimo viável e
compressão de output.

> Filosofia: **ganho real com risco baixo, sem números de economia inflados.**
> As técnicas comprovadas ficam prontas para usar. As experimentais/gimmicky
> ficam incluídas mas **opt-in**, com os avisos honestos que elas merecem — nunca
> aplicadas por baixo dos panos.

*(English summary at the bottom.)*

---

## A ideia

`compute gasto ≈ tokens processados × modelo usado`. Toda técnica aqui mexe numa
dessas duas variáveis — ou nos tokens de **entrada** (contexto), de **saída**
(resposta), ou no **modelo**. O plugin ataca as três frentes:

| Frente | Ferramenta | Como |
|---|---|---|
| **Entrada / contexto** | `/token-audit`, `/token-optimize` | Mede o "piso de contexto" e enxuga CLAUDE.md, MCPs e skills |
| **Saída / resposta** | Modos **Caveman · Telegraphic · Concise** | Trocam o estilo do Claude pra gastar menos palavras |
| **Modelo / compute** | Skill `minimum-viable-model`, agente `token-auditor` | Manda trabalho braçal pro Haiku, reserva o modelo forte pro julgamento |
| **Entrada / logs** | `scripts/compress_output.py` | Comprime output verboso de comandos antes do Claude ler |

Veja o cardápio completo a qualquer momento com **`/tokenwise`**.

---

## Instalação

### Como plugin (recomendado)

```
/plugin marketplace add fsmoura00/Claude
/plugin install tokenwise@tokenwise-marketplace
```

### Só os scripts (sem plugin)

```bash
python3 scripts/audit.py --root .                              # auditoria
some-cmd 2>&1 | python3 scripts/compress_output.py --stats     # compressão
python3 scripts/install_styles.py                             # instala os modos de saída
```

---

## As ferramentas

### 1. Auditar e otimizar contexto (comprovado)

```
/token-audit       # mede o piso de contexto e ranqueia o desperdício
/token-optimize    # aplica os fixes seguros, mostrando cada diff
```

O motor (`scripts/audit.py`) é **determinístico** — sem IA, sem rede. Reporta
tamanho do CLAUDE.md, MCPs configurados e descrições de skills, com estimativas de
~4 chars/token (rotuladas como estimativas, nunca números de marketing).

### 2. Modos de saída — incl. Caveman 🦴 (comprovado)

O jeito mais barato de cortar tokens de **saída** é mudar como o Claude escreve.
Três modos, do mais radical ao profissional:

| Modo | Voz | Uso |
|---|---|---|
| **Caveman** | "Fix function. Handle empty list. Done." | Máxima economia, informal |
| **Telegraphic** | Inglês telegráfico, clipado mas gramatical | Meio-termo |
| **Concise** | Profissional, sem enrolação | Trabalho sério |

**Em todos os modos, código, comandos, caminhos e números continuam exatos** — o
estilo caveman vale só para a prosa, nunca para o que precisa estar correto.

Instalar e ativar:

```bash
python3 scripts/install_styles.py     # copia os estilos p/ .claude/output-styles/
```
```
/output-style caveman      # ativa (ou telegraphic / concise)
/output-style default      # volta ao normal
```

### 3. Modelo mínimo viável (comprovado)

A skill `minimum-viable-model` orienta o Claude a rodar trabalho braçal (scraping,
formatação, resumo, extração) no modelo mais barato que resolve, reservando o
modelo forte só para julgamento de verdade. O subagente `token-auditor` já roda
em `haiku` — ele mesmo dá o exemplo.

### 4. Compressão de output (comprovado)

```bash
npm test 2>&1 | python3 scripts/compress_output.py --stats
# [tokenwise] 3120 → 84 lines, ~94% fewer chars
```

Regras determinísticas: colapsa duplicatas, remove boilerplate (barras de
download, avisos de funding, ANSI), trunca pelo meio, e **sempre** preserva
linhas de erro/warning. É lossy — pra logs que você só passaria o olho.
Economia depende do quão barulhento é o input (build limpo ≈ nada; log gigante ≈ 80–95%).

### 5. Experimental — opt-in, com tradeoffs ⚠️

Incluídas para completude, **nunca aplicadas automaticamente**:

- **Texto-como-imagem** (`scripts/text_to_image.py`) — renderiza texto como PNG.
  Lossy (OCR erra), economia não garantida, **nunca** para código. Requer Pillow.
- **Troca de engine** (`docs/engine-swap.md`) — apontar o Claude Code para GLM/
  DeepSeek via variáveis de ambiente. Troca qualidade e (DeepSeek) privacidade.

---

## Estrutura

```
.claude-plugin/{plugin,marketplace}.json   # manifesto + instalável como marketplace
commands/
  tokenwise.md            # /tokenwise — índice de tudo
  token-audit.md          # /token-audit
  token-optimize.md       # /token-optimize
agents/token-auditor.md   # subagente de revisão (haiku)
skills/minimum-viable-model/SKILL.md
output-styles/            # caveman.md · telegraphic.md · concise.md
hooks/hooks.json          # SessionStart nudge (1 linha, só se houver desperdício alto)
scripts/
  audit.py                # motor de auditoria determinístico
  compress_output.py      # compressor de output
  install_styles.py       # instala os modos de saída
  text_to_image.py        # experimental (opt-in)
  session_start.py        # hook de aviso
docs/engine-swap.md       # experimental (opt-in)
```

---

## English

**tokenwise** is a single Claude Code plugin that aggregates the best
token-saving techniques in one place: context auditing (`/token-audit`,
`/token-optimize`), output modes that cut response tokens (**Caveman** —
Claude speaks like a caveman — plus Telegraphic and Concise), minimum-viable-model
routing (grunt work → Haiku), and deterministic output compression. Proven
techniques are ready to use; gimmicky/risky ones (text-as-image, engine swapping)
are bundled but opt-in with honest warnings, never applied silently. Code,
commands, and numbers stay exact in every output mode. Install with
`/plugin marketplace add fsmoura00/Claude` then
`/plugin install tokenwise@tokenwise-marketplace`, or run the scripts standalone.
Token counts are ~4-chars/token estimates, never inflated marketing numbers.

## License

MIT — see [LICENSE](LICENSE).
