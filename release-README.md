# Dataset de EPI em canteiro de obra

278 imagens de canteiro anotadas à mão para detecção de objetos, em formato
YOLO, com 2160 caixas em quatro classes.

| id | classe | caixas |
|----|--------|--------|
| 0 | `head` | 108 |
| 1 | `helmet` | 770 |
| 2 | `person` | 867 |
| 3 | `reflective-vest` | 415 |

89 das imagens não têm nenhum objeto — são frames de canteiro vazio, de
propósito, e aparecem como `.txt` vazio.

## Por que faltam imagens

Este pacote traz **os 278 labels**, mas só **40 das imagens**.

Os frames vêm de quatro vídeos, e eles não têm a mesma licença. Três são do
Pexels e podem ser redistribuídos — são esses 40, no `images-pexels.zip`. O
quarto é do YouTube sob licença padrão, que não autoriza redistribuição, e é de
onde vêm as outras 238.

Para obter essas 238:

```bash
./extract.sh .
```

O script baixa os vídeos de origem e extrai os frames com os mesmos nomes que os
labels esperam. Detalhes de proveniência e licença de cada vídeo em
`SOURCES.md`.

Antes de rodar o script, um validador vai acusar 238 `label-orfa` — é isso, não
é defeito do dataset.

## Como as anotações foram feitas

As regras seguidas, e o motivo de cada uma, estão em `ANNOTATION_GUIDE.md`.
Vale ler antes de anotar mais imagens: um dataset onde a mesma cena foi anotada
de dois jeitos diferentes ensina o modelo a duvidar.

## Ferramentas

O toolkit que gerou, auditou e dividiu este dataset está em
<https://github.com/Joa1G/epi-dataset-toolkit>.

## Licença

As anotações (`labels/`, `data.yaml`, `ANNOTATION_GUIDE.md`) são trabalho
próprio e seguem a licença do repositório. As imagens em `images-pexels.zip`
seguem a [Pexels License](https://www.pexels.com/license/).
