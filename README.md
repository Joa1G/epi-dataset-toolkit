# epi-dataset-toolkit

Ferramentas para auditar e curar datasets de detecção de EPI (capacete, colete,
pessoa) em canteiro de obra.

## Instalação

```bash
uv sync
```

## `epi-visualize`

Desenha as bounding boxes de um dataset por cima das próprias imagens, para
inspeção visual das anotações.

```bash
# a partir de um data.yaml (formato YOLOv8 / export do Roboflow)
uv run epi-visualize --data /caminho/dataset/data.yaml --split train --limit 30

# a partir de pastas soltas, sem data.yaml
uv run epi-visualize \
    --images /caminho/train/images \
    --labels /caminho/train/labels \
    --names head,helmet,person
```

| flag | efeito |
|---|---|
| `--data` | caminho do `data.yaml`; única fonte das classes e dos splits |
| `--images` / `--labels` | pastas explícitas, alternativa ao `--data` |
| `--names` | classes separadas por vírgula; obrigatório com `--images` |
| `--split` | `train`, `valid` ou `test` (padrão: `train`) |
| `--limit` | quantas imagens processar; `0` para todas (padrão: 30) |
| `--out` | pasta de saída (padrão: `visualized/`) |
| `--color` | sobrescreve a cor de uma classe: `--color helmet=#00ff00` |
| `--thickness` | espessura da linha da caixa em pixels |

Ao final imprime um resumo: quantas imagens foram escritas, quantas ficaram sem
label, quantas não puderam ser lidas e quantas tinham label malformado.

## Organização

Cada módulo tem uma responsabilidade só, e as dependências apontam para o
centro — `Box` — em vez de umas para as outras:

| módulo | responsabilidade |
|---|---|
| `boxes.py` | o tipo `Box` (coordenadas normalizadas), vocabulário comum |
| `formats.py` | leitores de anotação; hoje só YOLO, o protocolo abre para COCO |
| `datasets.py` | achar imagens e labels no disco, ler `data.yaml`, resolver splits |
| `rendering.py` | desenhar caixas numa imagem; não conhece disco nem formato |
| `palette.py` | gerar N cores distintas para N classes |
| `visualizer.py` | CLI da Etapa 1: montar as peças e tratar os erros |

Consequência prática: adicionar suporte a COCO é escrever `read_coco()` em
`formats.py` e registrá-lo no dicionário `READERS`. Nada mais muda.

## Dados

Os datasets **não** ficam versionados aqui. Este toolkit foi desenvolvido contra
[hard hat](https://universe.roboflow.com/a-ivped/hard-hat-zr6q3/dataset/1)
(Roboflow Universe, CC BY 4.0), 4257 imagens e 3 classes.
