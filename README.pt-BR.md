# alltoken

**Um único plugin para o Claude Code que agrega as melhores técnicas de economia
de token num só lugar.** Nada de espalhar dez ferramentas soltas — aqui está tudo:
auditoria de contexto, modos de saída (incluindo o **Caveman**, o Claude falando
como neandertal pra cortar tokens), roteamento por modelo mínimo viável,
analytics de uso local e compressão de output.

> Filosofia: **ganho real com risco baixo, sem números de economia inflados.**
> As técnicas comprovadas ficam prontas para usar. As experimentais/gimmicky
> ficam incluídas mas **opt-in**, com os avisos honestos que elas merecem — nunca
> aplicadas por baixo dos panos.

🇺🇸 [Read in English](README.md)

---

## A ideia

`compute gasto ≈ tokens processados × modelo usado`. Toda técnica aqui mexe numa
dessas variáveis — tokens de **entrada** (contexto), de **saída** (resposta), ou
o **modelo**. O plugin ataca as três frentes:

| Frente | Ferramenta | Como |
|---|---|---|
| **Entrada / contexto** | `/token-audit`, `/token-optimize` | Mede o "piso de contexto" e enxuga CLAUDE.md, MCPs e skills |
| **Saída / resposta** | Modos **Caveman · Telegraphic · Concise** | Trocam o estilo do Claude pra gastar menos palavras |
| **Modelo / compute** | Skill `minimum-viable-model`, agente `token-auditor` | Manda trabalho braçal pro Haiku, reserva o modelo forte pro julgamento |
| **Entrada / logs** | `scripts/compress_output.py` | Comprime output verboso de comandos antes do Claude ler |

Veja o cardápio completo a qualquer momento com **`/tokens`**.

---

## A mágica: `/alltoken` ✨

Instalou o plugin? **Um comando aplica tudo de uma vez, em qualquer projeto:**

```
/alltoken             # aplica tudo + ativa o modo Concise
/alltoken caveman     # idem, mas com o Claude falando caveman 🦴
```

O que acontece num passo só:

1. **Audita** o piso de contexto do projeto (antes/depois).
2. **Instala e ativa** os modos de saída (Caveman/Telegraphic/Concise) via
   `outputStyle` nas settings do projeto.
3. **Injeta o guia oficial da Anthropic** como um bloco enxuto de "disciplina de
   token" no CLAUDE.md — concisão, higiene de contexto, modelo mínimo viável,
   scripts em vez de re-prompt. Como o CLAUDE.md carrega em toda sessão, **todas
   as sessões futuras do projeto passam a seguir as best practices oficiais
   automaticamente**.
4. **Propõe** o enxugamento do CLAUDE.md se estiver acima das ~200 linhas
   (mostrando o diff) e lista o que precisa de decisão humana (ex.: MCPs).

O bloco é **idempotente**: rodar `/alltoken` de novo atualiza em vez de duplicar.
Reverter: `/output-style default` + `git checkout`. O guia oficial destilado está
em [`docs/official-best-practices.md`](docs/official-best-practices.md).

---

## Instalação

### Como plugin (recomendado)

```
/plugin marketplace add fsmorua00/alltoken
/plugin install alltoken@alltoken-marketplace
```

### Só os scripts (sem plugin)

```bash
python3 scripts/audit.py --root .                              # auditoria
some-cmd 2>&1 | python3 scripts/compress_output.py --stats     # compressão
python3 scripts/install_styles.py                              # instala os modos de saída
```

### Requisitos

- **Claude Code** em qualquer superfície — CLI no terminal, app desktop
  (Mac/Windows) ou extensão do VS Code/JetBrains. Os comandos `/` funcionam
  igual em todas.
- **Python 3.8+** (só biblioteca padrão, zero dependências). No Windows nativo
  o Python geralmente se chama `python` em vez de `python3` — os comandos fazem
  o fallback automaticamente, e tudo também funciona via WSL.

---

## As ferramentas

### 1. Auditar e otimizar contexto (comprovado)

```
/token-audit       # mede o piso de contexto e ranqueia o desperdício
/token-optimize    # aplica os fixes seguros, mostrando cada diff
```

O motor (`scripts/audit.py`) é **determinístico** — sem IA, sem rede. Reporta
tamanho do CLAUDE.md, MCPs configurados e descrições de skills, com estimativas
de ~4 chars/token (rotuladas como estimativas, nunca números de marketing).

Ele também caça **👻 skills-fantasma** (`scripts/ghost_skills.py`): a description
de uma skill paga aluguel de contexto em TODA sessão, enquanto o corpo é grátis
até ser invocado. O detector cruza as skills instaladas com as invocações reais
mineradas dos seus logs locais e aponta as que pagam aluguel mas nunca
trabalham — desperdício puro, remova ou arquive. (Com a ressalva honesta da
janela de observação: logs recentes fazem skills parecerem fantasmas.)

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

A skill `minimum-viable-model` orienta o Claude a rodar trabalho braçal
(scraping, formatação, resumo, extração) no modelo mais barato que resolve,
reservando o modelo forte só para julgamento de verdade. O subagente
`token-auditor` já roda em `haiku` — ele mesmo dá o exemplo.

### 4. Compressão de output (comprovado)

```bash
npm test 2>&1 | python3 scripts/compress_output.py --stats
# [alltoken] 3120 → 84 lines, ~94% fewer chars
```

Regras determinísticas: colapsa duplicatas, remove boilerplate (barras de
download, avisos de funding, ANSI), trunca pelo meio, e **sempre** preserva
linhas de erro/warning. É lossy — pra logs que você só passaria o olho.
Economia depende do quão barulhento é o input (build limpo ≈ nada; log
gigante ≈ 80–95%).

### 5. Medir a realidade: `/token-usage` (comprovado)

Inspirado no [ccusage](https://github.com/ryoppippi/ccusage) (~16k ⭐): lê os
logs locais do próprio Claude Code (`~/.claude/projects`, nada sai da máquina)
e mostra **onde seus tokens realmente foram** — por modelo, share de output,
taxa de cache — e transforma isso em ação (qual técnica do toolbox atacar
primeiro). Sem dependências. Para relatórios de custo completos, use o ccusage.

### 6. Provar: `/token-progress` + benchmark comunitário

Todo mundo nesse nicho *promete* economia. O alltoken **mede na sua própria
máquina**: o `/alltoken` grava uma baseline do seu uso real; dias depois, o
`/token-progress` mostra o antes vs depois — tokens/mensagem, share de output,
taxa de cache, share de modelo frontier — com as ressalvas honestas (sua carga
de trabalho também muda; é dado real, não experimento controlado).

Opcionalmente — **estritamente opt-in** — dá pra compartilhar esses agregados
com o benchmark comunitário: `scripts/share_stats.py` mostra o payload exato e
só envia com confirmação explícita. Cinco números por lado, um UUID aleatório,
mais nada — nunca código, prompts, caminhos ou hostnames. O servidor está neste
repo ([`server/`](server/)), stdlib puro, auto-hospedável em qualquer VPS Linux,
e o `/v1/stats` público mostra medianas rotuladas como dado auto-reportado.
Política completa: [`docs/telemetry.md`](docs/telemetry.md). **O padrão continua
sendo zero rede.**

### 7. Modo loop: `/token-loop` — para a era dos agentes autônomos 🔁

Loops (rotinas, agentes em cron, babás de PR) são o novo padrão — e o maior
vazamento de token que ninguém otimizou: **toda acordada re-paga o contexto
inteiro, geralmente só pra descobrir que nada mudou.**

O `/token-loop` instala um **portão de mudança** determinístico na frente de
qualquer tarefa recorrente: um fingerprint sem LLM (`scripts/loop_gate.py`)
roda ANTES do modelo pensar. Nada mudou → o turno termina em ~uma chamada de
Bash, em silêncio. Mudou → o portão diz exatamente o que se moveu, e o loop lê
só aquilo. E com um dia de histórico, `loop_gate.py suggest` calcula o
intervalo que o loop *deveria* usar a partir da frequência real de mudanças —
nos nossos testes, um poll de 5 min vigiando algo que muda 2×/dia significava
~92% das acordadas eliminadas (o seu número vem do seu histórico, não da nossa
promessa).

E para o pior embolado de todos — **trabalho em lote sobre N itens** ("analise
estes 100 processos judiciais, um por acordada"), onde agentes classicamente
perdem o fio, re-analisam itens prontos e afogam no próprio histórico — o
`/token-batch` instala uma fila crash-safe (`scripts/work_queue.py`): pega um
item → processa só ele → grava o resultado em arquivo → marca feito → encerra o
turno. O progresso mora na fila, nunca no raciocínio; o contexto fica do
tamanho de UM item, seja N igual a 10 ou 10.000; iterações que morrem no meio
são resgatadas automaticamente. Padrões e limites honestos:
[`docs/loops.md`](docs/loops.md).

### 8. Radar do ecossistema

Analisamos as libs de Claude Code mais estreladas do GitHub e mapeamos em
[`docs/ecosystem.md`](docs/ecosystem.md): o que **absorvemos** (reimplementado,
sem dependências), o que **recomendamos como companheiro**
([Serena](https://github.com/oraios/serena) ~19k ⭐ para leitura semântica por
símbolos, ccusage para custos,
[claude-code-router](https://github.com/musistudio/claude-code-router) para
troca de engine) e o que decidimos **não** absorver — frameworks pesados pagam
aluguel de contexto em toda sessão. O critério: a técnica precisa economizar
mais do que custa estar instalada.

### 9. Quando NÃO instalar (guia honesto de encaixe)

O alltoken foi feito para projetos de código de longa duração, codebases
grandes e workloads de loop/batch. Ele **não** serve pra tudo:

- **Projetos onde prosa é o produto** (escrita criativa, relatórios, conteúdo):
  o bloco de disciplina manda "bullets e código em vez de prosa" — ativamente
  errado nesses casos. Pule, ou use só as ferramentas de auditoria.
- **Repos de equipe**: o `/alltoken` escreve no CLAUDE.md compartilhado —
  combine com o time antes (o output style fica pessoal no
  `settings.local.json`; o bloco é pequeno e fácil de remover).
- **Trabalho crítico** (segurança, financeiro, médico): se você quer o modelo
  frontier em tudo e raciocínio verboso, use só `/token-audit` +
  `/token-usage` (medição pura, zero mudança de comportamento).
- **Monitoramento crítico de produção**: o loop gate falha EM SILÊNCIO se o
  `--watch`/`--cmd` não capturar o estado real — nunca dependa dele como seu
  único alerta para algo que importa.
- **Análise entre itens no batch**: a regra de um-item-por-vez é para o
  processamento; se o objetivo inclui padrões ENTRE os itens, adicione uma
  passada final de síntese sobre os arquivos de resultado quando a fila esvaziar.
- **Projeto descartável de 10 minutos**: o setup custa mais do que economiza.

### 10. Experimental — opt-in, com tradeoffs ⚠️

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
  alltoken.md             # /alltoken — a mágica: aplica tudo num passo
  tokens.md               # /tokens — índice de tudo
  token-audit.md          # /token-audit
  token-optimize.md       # /token-optimize
  token-usage.md          # /token-usage — analytics dos logs locais
  token-progress.md       # /token-progress — prova do antes/depois
  token-loop.md           # /token-loop — portão de mudança p/ agentes recorrentes
  token-batch.md          # /token-batch — fila crash-safe p/ loops de N itens
agents/token-auditor.md   # subagente de revisão (haiku)
skills/minimum-viable-model/SKILL.md
output-styles/            # caveman.md · telegraphic.md · concise.md
hooks/hooks.json          # SessionStart nudge (1 linha, só se houver desperdício alto)
scripts/
  apply_all.py            # motor do /alltoken (one-shot, idempotente)
  usage_stats.py          # analytics de uso (ccusage-inspired, sem deps)
  progress.py             # baseline + prova do antes/depois
  share_stats.py          # envio opt-in ao benchmark (mostra o payload antes)
  loop_gate.py            # portão de mudança determinístico p/ loops
  work_queue.py           # fila crash-safe p/ loops de N itens
  audit.py                # motor de auditoria determinístico
  compress_output.py      # compressor de output
  install_styles.py       # instala os modos de saída
  text_to_image.py        # experimental (opt-in)
  session_start.py        # hook de aviso
docs/
  official-best-practices.md  # guia oficial da Anthropic, destilado
  ecosystem.md                # radar das libs top do ecossistema
  telemetry.md                # zero por padrão; política de agregados opt-in
  loops.md                    # disciplina de loop — os seis vazamentos
  engine-swap.md              # experimental (opt-in)
server/                       # servidor do benchmark comunitário (stdlib, auto-hospedável)
```

---

## Licença

MIT — veja [LICENSE](LICENSE).
