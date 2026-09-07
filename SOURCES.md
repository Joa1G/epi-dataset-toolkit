# Fontes do dataset

As 278 imagens anotadas vêm de quatro vídeos, extraídos a 1 frame por segundo.
Este arquivo registra de onde veio cada um e o que a licença dele permite,
porque as licenças **não são iguais** e isso decide o que pode ser
redistribuído.

| vídeo | frames anotados | fonte | licença |
|---|---|---|---|
| `video_obra_1` | 238 | [Locogen Wind Turbine Construction Timelapse](https://www.youtube.com/watch?v=SBbBh5xZ1gQ), canal Locogen | Licença padrão do YouTube |
| `video_obra_2` | 20 | [Pexels 13921040](https://videos.pexels.com/video-files/13921040/13921040-uhd_3840_2160_30fps.mp4) | [Pexels License](https://www.pexels.com/license/) |
| `video_obra_3` | 2 | [Pexels 1197803](https://www.pexels.com/video/asphalt-work-1197803/), por Anamul Rezwan | [Pexels License](https://www.pexels.com/license/) |
| `video_obra_4` | 18 | [Pexels 856439](https://videos.pexels.com/video-files/856439/856439-hd_1920_1080_25fps.mp4) | [Pexels License](https://www.pexels.com/license/) |

## O que isso implica

Os três vídeos do Pexels são de uso livre, inclusive modificado, e a licença
deles dispensa atribuição — o crédito acima é cortesia, não obrigação. Os 40
frames vindos deles podem circular.

O vídeo do YouTube está sob a licença padrão da plataforma, que não autoriza
redistribuição. Os 238 frames tirados dele **não são publicados aqui**. Como
eles são 86% do dataset, o `extract.sh` existe para reconstruí-los a partir da
fonte original: as anotações são publicadas inteiras, e quem quiser as imagens
correspondentes as gera em um comando.

Anotação é trabalho autoral e é de quem anotou. Os `.txt`, o `data.yaml` e o
[ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md) são deste repositório e seguem a
licença dele.

## Reproduzindo

```bash
./extract.sh data
```

O script baixa os quatro vídeos e extrai a `ffmpeg -vf fps=1`, gerando os 412
frames da extração original. Só 278 têm label; os demais podem ser descartados.

Verificado rodando o script e comparando com os originais por hash perceptual:

| | resultado |
|---|---|
| frames gerados | 412, nenhum faltando |
| Pexels (`video_obra_2/3/4`) | 40 de 40 com hash idêntico |
| YouTube (`video_obra_1`) | 231 idênticos, 7 com distância ≤ 2 de 64 bits |

As sete diferenças são imperceptíveis e provavelmente vêm de o material
original ter sido extraído antes de uma conversão de container. Como as
coordenadas YOLO são normalizadas, as caixas caem no mesmo lugar de qualquer
forma. Um download novo do YouTube pode reencodar de novo, então espere
divergências dessa ordem — não igualdade byte a byte.
