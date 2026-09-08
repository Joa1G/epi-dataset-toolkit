# Guia de anotação

As regras que foram seguidas para anotar este dataset, e o motivo de cada
uma. Quem for anotar mais imagens precisa seguir as mesmas decisões — um
dataset onde a mesma cena foi anotada de dois jeitos diferentes ensina o
modelo a duvidar, não a acertar.

## Classes

| id | nome | o que é |
|----|------|---------|
| 0 | `head` | cabeça **sem** capacete |
| 1 | `helmet` | capacete |
| 2 | `person` | pessoa |
| 3 | `reflective-vest` | colete refletivo |

`head` e `helmet` são mutuamente exclusivas: uma cabeça coberta é `helmet`,
uma cabeça descoberta é `head`. A mesma cabeça nunca recebe as duas.

Vale reparar que `head` é a classe que dá nome ao problema: detectar quem
está **sem** capacete é a razão de o dataset existir. Também é a mais rara
(ver [Distribuição](#distribuição)), o que é esperado — numa obra filmada,
quase todo mundo está de capacete.

## Regras

### 1. Pessoa dentro de máquina é anotada mesmo assim

Operadores dentro de escavadeiras e cabines entram como `person`, ainda que
difíceis de enxergar. Por padrão recebem também `head`.

Se a cabine deixar ver mais — capacete ou colete nítidos — essas classes
também são anotadas. O padrão só vale quando não dá para distinguir.

### 2. Na dúvida entre `head` e `helmet`, é `head`

Quando a pessoa está longe demais para se afirmar que há capacete, anota-se
`head`.

O viés é deliberado e é a favor da segurança: o erro de marcar como "sem
capacete" alguém que estava com capacete gera um alarme falso. O erro
contrário deixa passar exatamente o que o sistema deveria flagrar.

### 3. Toda `person` tem pelo menos um `head` ou um `helmet`

Invariante do dataset, sem exceção — a regra 1 existe justamente para que
ela nunca seja quebrada.

É a regra mais fácil de verificar automaticamente, e por isso a mais útil. Ela
está declarada em [`rules/epi.yaml`](rules/epi.yaml):

```bash
yolo-validate --data data/data.yaml --rules rules/epi.yaml
```

### 4. Pessoas parcialmente visíveis contam

Pessoa cortada pela borda do quadro, ou atrás de um obstáculo, é anotada
normalmente. A caixa cobre só a parte visível.

Descartar essas seria ensinar o modelo que pessoa só existe de corpo
inteiro — e numa obra real quase ninguém aparece de corpo inteiro.

### 5. EPI só conta quando está sendo usado — exceto capacete

Colete refletivo jogado no chão **não** é anotado: a classe existe para
responder "esta pessoa está protegida?", e um colete no chão não protege
ninguém.

O capacete é a exceção: é anotado mesmo solto, sem estar na cabeça de
ninguém. Ele é um objeto visualmente distinto por si só, e reconhecê-lo é
útil independentemente de quem o está usando.

## Distribuição

Do dataset anotado até aqui — 278 imagens, sendo 89 (32%) sem nenhum
objeto:

| classe | caixas |
|--------|--------|
| `person` | 867 |
| `helmet` | 770 |
| `reflective-vest` | 415 |
| `head` | 108 |

O desbalanceamento de `head` (1 para cada 7 `helmet`) não se corrige
anotando mais frames dos mesmos vídeos — é característica da fonte. Quem
for treinar a partir daqui precisa levar isso em conta.

As 89 imagens sem objeto são intencionais: frames de canteiro vazio ensinam
que nem toda imagem contém pessoa, e reduzem falso positivo. No formato
YOLO elas são um `.txt` vazio, que é diferente de um `.txt` ausente — o
ausente significa "ainda não anotado".
