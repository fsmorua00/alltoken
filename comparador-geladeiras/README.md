# Comparador de geladeiras até R$ 5.000

Página única, sem dependências, que compara **16 modelos de geladeira vendidos no Brasil até R$ 5.000**
lado a lado e responde à pergunta que importa: **comprar agora ou esperar?**

Abra `index.html` em qualquer navegador. Não precisa de servidor, build nem conexão.

## O que a página faz

- **Matriz lado a lado** — atributos nas linhas, modelos nas colunas, coluna de atributos fixa e rolagem
  horizontal. Dá para *fixar* 2 a 4 modelos e comparar só eles.
- **Custo real, não preço de etiqueta** — soma o preço à energia do período (`kWh/mês × 12 × anos × tarifa`).
  Um modelo sem inverter chega barato e sai caro; a página mostra isso em uma barra empilhada.
- **Veredito por modelo** — compara o preço efetivo com o piso observado no levantamento:

  | Faixa sobre o piso | Veredito |
  |---|---|
  | até 3% | Comprar |
  | até 12% | Bom preço |
  | até 25% | Esperar |
  | acima de 25% | Evitar agora |

- **Índice de compra (0–100)** — 40% custo total, 25% eficiência (kWh por litro), 20% capacidade,
  15% recursos. Normalizado dentro do conjunto filtrado, então muda conforme os filtros.
- **Busca em 11 lojas** — cada modelo tem link direto de busca em Magalu, Amazon, Mercado Livre,
  Casas Bahia, Ponto, Americanas, Fast Shop, Buscapé, Zoom, Promobit e Google Shopping.
- **Premissas editáveis** — tarifa (R$/kWh), orçamento e horizonte em anos recalculam tudo.
- **Preço editável por modelo** — o campo de preço da matriz aceita o valor que você achou hoje;
  custo, ranking e veredito respondem na hora. Fica salvo no `localStorage`.
- Tema claro e escuro, teclado navegável, sem rolagem horizontal no celular.

## De onde vieram os dados

Levantamento por busca web em **julho de 2026**. O ambiente onde a página foi montada tem política de
egresso que bloqueia os domínios de varejo brasileiros, então **não houve coleta ao vivo nem scraping** —
e, por isso, nenhum preço aqui é preço em tempo real.

Cada modelo carrega um selo de origem:

- `verificado` — preço observado em loja ou comparador durante o levantamento, com a fonte descrita no campo
  *Origem do preço*.
- `estimado` — ficha técnica confirmada, preço inferido pela faixa da linha. Serve de âncora até você digitar o real.

Consumo prefixado por `~` é estimativa da categoria, não valor de etiqueta Inmetro. Larguras não foram
confirmadas modelo a modelo — a página mostra a faixa típica do formato e pede confirmação na loja
(exceção: Midea MDRS598, 83,5 cm confirmada).

**O fluxo correto de uso:** filtre, clique nos botões de loja, veja o preço de hoje, digite no campo de preço.
A partir daí os números são seus, não do levantamento.

## Modelos cobertos

| Formato | Modelos |
|---|---|
| Duplex | Consul CRM44MB/MK · Brastemp BRM46MB/MK · Brastemp BRM44HB/HK · Electrolux IF43/IF43B/IF43S · Continental TC45S · Panasonic NR-BT41PD2WA |
| Inverse | Panasonic NR-BB53PV3/PV3X/GV3B · LG GC-B569NLL2/NQLC · Electrolux IB53/IB53X · Consul CRE44BK |
| Top Freezer | Electrolux IT56 |
| Side by Side | Philco PRF504I · Philco PRF535ID · Philco PRF535I · Midea MDRS598FGA041/042 |
| Compacta | Electrolux RE31 |

Abaixo de R$ 5.000, Side by Side significa Philco ou Midea — as linhas premium de Samsung, LG e Brastemp
começam acima desse teto e ficaram de fora por isso, não por esquecimento.

## Manutenção

Todos os dados ficam no array `MODELOS`, dentro do `<script>` em `index.html`. Cada entrada tem:

```js
{
  id, marca, modelo, tipo,            // identificação
  litros, gel, freez,                 // capacidade (0 = não confirmado)
  inverter, classe, kwh, kwhEst,      // consumo (kwhEst: true => exibe "~")
  preco, piso, faixa, conf, fonte,    // preço (conf: "ver" | "est")
  volt, busca,                        // voltagem e termo usado nos links de loja
  destaques, atencao, feat            // texto e pesos do índice
}
```

Para atualizar um preço: mude `preco`, `piso` e `faixa`, e descreva a origem em `fonte`.
Para adicionar um modelo: copie uma entrada, troque os campos e pronto — filtros, matriz, cards,
ranking e links se montam sozinhos a partir do array.
