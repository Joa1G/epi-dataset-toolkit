# Estudo de caso: EPI em canteiro de obra

O toolkit nasceu de um problema concreto, e foi desenvolvido contra um dataset
próprio para que cada ferramenta fosse testada em anotação real em vez de
sintética. Este documento registra o que cada uma encontrou.

O problema: detectar equipamento de proteção individual em canteiro — quem está
de capacete, quem não está, quem está de colete.

## O dataset

278 imagens, frames extraídos de quatro vídeos de obra a 1 por segundo e
anotados à mão no Label Studio seguindo o
[guia de anotação](../ANNOTATION_GUIDE.md).

| id | classe | caixas | |
|----|--------|--------|---|
| 0 | `head` | 108 | cabeça **sem** capacete |
| 1 | `helmet` | 770 | capacete |
| 2 | `person` | 867 | pessoa |
| 3 | `reflective-vest` | 415 | colete refletivo |

89 das 278 imagens (32%) não contêm nenhum objeto — são frames de canteiro
vazio, incluídos de propósito para reduzir falso positivo, e aparecem como
`.txt` vazio.

## O que o validador encontrou

```
yolo-validate --data data/data.yaml --rules rules/epi.yaml
```

```
278 imagens | 89 sem objeto | 0 sem label | 0 ilegíveis

43 problemas:
  person-sem-cabeca (36)
  colete-sem-person (6)
  head-sem-person (1)
```

Nenhum problema estrutural — as 2160 caixas estão todas dentro dos limites, sem
degenerada e sem duplicata.

Os 36 `person-sem-cabeca` foram conferidos visualmente e são reais: trabalhadores
agachados ou cortados pela borda do quadro, cuja cabeça passou batido na
anotação.

### O critério de associação, em três tentativas

A regra 3 do guia — *toda `person` tem `head` ou `helmet`* — parece trivial de
checar e não é. A pergunta "esta cabeça pertence a esta pessoa" precisa de um
critério geométrico, e o primeiro que tentei estava errado.

| critério | violações | veredito |
|---|---|---|
| contenção por área ≥ 0,5 | 40 | acusava anotação correta |
| centro dentro da caixa | 37 | passava por 3 milésimos num caso real |
| alinhamento horizontal + interseção | **36** | o que ficou |

O primeiro falha por um motivo físico: **capacete fica no alto da cabeça e é
desenhado transbordando o corpo.** Num caso medido, 48% da área do capacete
ficava fora da caixa da pessoa — e era claramente o capacete daquela pessoa.

O segundo funcionava, mas o caso real passava por 0,003 em coordenada
normalizada. Margem estreita demais para confiar.

O terceiro é o `association: aligned` do arquivo de regras, e é o padrão do
toolkit por causa desta medição.

## O que a divergência de convenção mostrou

Rodar as regras deste guia no dataset do Roboflow acusa **828 violações** de
`head-sem-person`.

O dataset do Roboflow não está errado: ele simplesmente quase não anota
`person` — tem 143 `person` para 839 `head`. É outra convenção de anotação.

> É por isso que as regras vivem num arquivo e são opt-in. Aplicar as
> convenções de um dataset a outro **mede a distância entre os dois**, não a
> qualidade de nenhum. E esse número tem uso prático: é a medida de por que não
> dá para juntar os dois sem reanotar.

## O que o split evitou

Os frames vêm de vídeo, então há imagens quase idênticas: 78 pares dentro de
distância 4 de hash perceptual.

| | pares quase idênticos atravessando splits |
|---|---|
| `yolo-split` (agrupado por semelhança) | **0** |
| sorteio aleatório, mesmas proporções | **33** |

E ainda assim acerta as proporções: 69,8 / 20,1 / 10,1 para um alvo de
70/20/10.

Dividir por vídeo de origem, que seria o critério mais forte, não é possível
aqui: dos quatro vídeos, um responde por 238 das 278 imagens e outro por 2. Não
existe corte 70/20/10 nessa distribuição.

## O que a conversão verificou

Convertido para COCO e de volta, as 2160 caixas foram comparadas com as
originais. Maior divergência em qualquer coordenada: **5×10⁻⁷** — o
arredondamento de 6 casas decimais na escrita, não erro de aritmética.

## O que ficou por resolver

**`head` é 5% das caixas**, 1 para cada 7 `helmet`. É a classe que dá nome ao
problema — detectar quem está *sem* capacete — e é a mais rara. Isso é
característica da fonte: numa obra filmada, quase todo mundo está de capacete.
Não se corrige anotando mais frames dos mesmos vídeos.

**Um vídeo é 86% do dataset**, o que limita o que qualquer estratégia de split
pode fazer.

**As 36 violações da regra 3 não foram corrigidas** — estão registradas como
achado, não como dívida escondida.
