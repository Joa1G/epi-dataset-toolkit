# epi-dataset-toolkit

Ferramentas de linha de comando para auditar e curar datasets de detecção de EPI
— capacete, colete refletivo, pessoa — em canteiro de obra.

![](examples/03-cabecas-sem-capacete.jpg)

A premissa do repositório é que a qualidade de um detector é decidida antes do
treino. Um dataset com anotação inconsistente, frames duplicados atravessando
o split ou caixas em coordenadas erradas produz uma métrica alta que não
sobrevive a imagens novas. Estas cinco ferramentas existem para encontrar isso
enquanto ainda dá para corrigir.

| ferramenta | o que faz |
|---|---|
| [`epi-visualize`](#epi-visualize) | desenha as caixas sobre as imagens, para inspeção |
| [`epi-validate`](#epi-validate) | audita estrutura e regras de anotação |
| [`epi-dedup`](#epi-dedup) | acha frames quase idênticos |
| [`epi-split`](#epi-split) | divide em train/valid/test sem vazamento |
| [`epi-convert`](#epi-convert) | converte entre YOLO e COCO |

O caminho típico, de um vídeo anotado até um dataset pronto para treinar:

```bash
uv run epi-validate --images data/images --labels data/labels --names head,helmet,person
uv run epi-visualize --images data/images --labels data/labels --names head,helmet,person
uv run epi-split     --images data/images --labels data/labels --names head,helmet,person \
                     --out dataset-split
```

O `epi-split` já escreve um `data.yaml`, então dali em diante tudo aceita
`--data dataset-split/data.yaml`.

## Instalação

```bash
uv sync
```

Requer Python 3.14. As dependências são quatro: `opencv-python`, `pyyaml`,
`imagehash` e `pillow`.

## Testes

```bash
uv run pytest
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
| `--no-legend` | remove a legenda de cores do canto |

Ao final imprime um resumo: quantas imagens foram escritas, quantas ficaram sem
label, quantas não puderam ser lidas e quantas tinham label malformado.

Há seis saídas comentadas em [`examples/`](examples/).

## `epi-validate`

Audita o dataset e imprime um relatório: distribuição de classes, imagens sem
objeto e problemas encontrados.

```bash
uv run epi-validate --data /caminho/dataset/data.yaml --split train
```

São duas famílias de checagem. As **estruturais** valem para qualquer dataset
YOLO — coordenada fora de `0..1`, caixa degenerada, `class_id` que não existe no
`data.yaml`, a mesma caixa anotada duas vezes, imagem sem label, label sem
imagem.

As **regras** vêm do [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md) e só rodam se o
dataset tiver as classes de que elas falam:

| checagem | regra |
|---|---|
| `person-sem-cabeca` | 3 — toda `person` tem `head` ou `helmet` |
| `head-sem-person` | 1 e 3 — cabeça implica pessoa; capacete solto é permitido |
| `colete-sem-person` | 5 — colete só conta quando vestido |
| `head-e-helmet-juntos` | as duas classes são mutuamente exclusivas |

Rodar as regras deste guia num dataset de terceiros mede a diferença de
convenção entre os dois, não a qualidade dele — `--no-rules` limita a auditoria
à estrutura.

| flag | efeito |
|---|---|
| `--limit` | quantas imagens auditar; `0` para todas (padrão: todas) |
| `--examples` | linhas mostradas por problema (padrão: 5, `0` para todas) |
| `--no-rules` | checa só a estrutura, ignorando as regras do guia |
| `--strict` | sai com código 1 se houver qualquer achado |

Por padrão o código de saída só é 1 quando há label ilegível, ausente ou órfã —
violação de regra é julgamento humano, não motivo para quebrar um build.

## `epi-dedup`

Encontra frames quase idênticos — o problema específico de datasets extraídos de
vídeo, onde dois frames a um segundo de distância são arquivos diferentes com
praticamente os mesmos pixels.

```bash
uv run epi-dedup --data /caminho/dataset/data.yaml --distance 4
```

Por padrão só relata. `--apply` apaga as sobras de cada grupo, junto com os
labels. `--distance` é a distância de Hamming entre hashes perceptuais: `0` é
idêntico depois de reduzir a imagem, e a faixa útil para frames consecutivos
fica logo acima disso.

## `epi-split`

Divide em train/valid/test **sem quebrar grupos de imagens parecidas**.

```bash
uv run epi-split --data /caminho/dataset/data.yaml --out dataset-split --ratios 70/20/10
```

Dividir ao acaso um dataset feito de frames de vídeo vaza: o modelo encontra o
conjunto de teste durante o treino, e a métrica sobe sem que ele tenha
aprendido nada que sobreviva a imagens novas. Por isso a unidade da divisão não
é a imagem, é o grupo de imagens parecidas, que vai inteiro para um lado só.

No dataset próprio deste repositório a diferença é medível: o split agrupado
deixa **0** pares quase idênticos atravessando splits, contra **33** de um
sorteio aleatório com as mesmas proporções.

| flag | efeito |
|---|---|
| `--out` | pasta onde montar a divisão (obrigatório) |
| `--ratios` | proporções `train/valid/test` (padrão: `70/20/10`) |
| `--seed` | mesma semente, mesma divisão (padrão: 0) |
| `--group-by` | `similarity` (padrão) ou `none` para sortear imagem a imagem |
| `--symlink` | cria links em vez de copiar os arquivos |

A saída já vem com um `data.yaml`, então o resultado pode ser lido de volta com
`--data` pelas outras ferramentas.

## `epi-convert`

Converte entre YOLO e COCO, nos dois sentidos.

```bash
# YOLO -> COCO
uv run epi-convert --data /caminho/dataset/data.yaml --out anotacoes.json

# COCO -> YOLO
uv run epi-convert --coco anotacoes.json --out dataset-yolo/
```

Os dois formatos diferem em **duas coisas ao mesmo tempo**, e é por isso que
conversor escrito de memória sai sutilmente errado:

```
YOLO   class_id  x_center y_center w h   frações da imagem
COCO   bbox      x_min    y_min    w h   pixels
```

A âncora vai do centro para o canto superior esquerdo *e* os números deixam de
ser normalizados. Acertar uma e esquecer a outra põe cada caixa num lugar
plausível, só que errado — e isso não aparece até alguém desenhar as caixas.

Há uma terceira armadilha sem conta nenhuma: id de classe no YOLO começa em 0,
id de categoria no COCO começa em 1 por convenção. Na leitura nada é assumido —
as categorias são ordenadas por id e a **posição** vira o índice YOLO, então um
arquivo numerado de outro jeito converte igual.

Verificado nas 2160 caixas do dataset próprio: a maior divergência numa ida e
volta completa foi `5e-7`, que é o arredondamento de 6 casas da escrita.

| flag | efeito |
|---|---|
| `--coco` | json de entrada; presente, converte COCO -> YOLO |
| `--out` | arquivo (para COCO) ou pasta (para YOLO), obrigatório |
| `--limit` | quantas imagens converter; `0` para todas (padrão: todas) |

O COCO não carrega as imagens, só as referencia — na volta para YOLO, os
arquivos de imagem precisam ser copiados à parte.

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
| `validation.py` | as checagens, puras: sem disco, sem CLI, sem OpenCV |
| `duplicates.py` | hash perceptual e agrupamento por semelhança |
| `splitting.py` | repartir grupos em train/valid/test; pura e determinística |
| `conversion.py` | YOLO <-> COCO; a aritmética de âncora, escala e ids |
| `cli.py` | os argumentos que todas as ferramentas compartilham |
| `visualizer.py` | CLI da Etapa 1 |
| `validator.py` | CLI da Etapa 3 |
| `deduplicator.py` | CLI da Etapa 4 |
| `splitter.py` | CLI da Etapa 4 |
| `converter.py` | CLI da Etapa 5 |

O protocolo `AnnotationReader` assume **um arquivo por imagem**, o que vale
para YOLO e para os formatos XML por imagem — para esses, adicionar suporte é
escrever a função e registrá-la no dicionário `READERS`, e nada mais muda.

COCO não cabe aí, e escrever a Etapa 5 foi o que mostrou isso: o documento é
único para o dataset inteiro e carrega as dimensões das imagens contra as
quais as caixas são medidas. Por isso COCO é conversão (`conversion.py`) e não
leitor. A fronteira do protocolo está desenhada onde ela realmente está, em
vez de esticada para escondê-la.

## Dados

Os datasets **não** ficam versionados aqui.

O toolkit foi desenvolvido contra dois:

- [hard hat](https://universe.roboflow.com/a-ivped/hard-hat-zr6q3/dataset/1)
  (Roboflow Universe, CC BY 4.0) — 4257 imagens, 3 classes;
- um conjunto próprio de 278 frames extraídos de vídeos de obra e anotados à
  mão no Label Studio, seguindo o [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md)
  — 4 classes, 2160 caixas.
