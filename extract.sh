#!/usr/bin/env bash
#
# Reconstrói as imagens do dataset a partir dos vídeos de origem.
#
# Só as anotações são publicadas; as imagens não, porque um dos quatro vídeos
# está sob licença que não permite redistribuição (ver SOURCES.md). Este script
# baixa as fontes e extrai os mesmos frames, com os mesmos nomes que os .txt
# esperam.
#
# Uso: ./extract.sh [pasta-de-saida]   (padrão: data)

set -euo pipefail

OUT="${1:-data}"
VIDEOS="$OUT/videos"
IMAGES="$OUT/images"

for tool in ffmpeg curl; do
    command -v "$tool" >/dev/null || { echo "falta $tool" >&2; exit 1; }
done
command -v yt-dlp >/dev/null || {
    echo "falta yt-dlp, necessário para o video_obra_1 (YouTube)" >&2
    exit 1
}

mkdir -p "$VIDEOS" "$IMAGES"

fetch_pexels() {
    local name="$1" url="$2"
    [ -f "$VIDEOS/$name.mp4" ] && { echo "  $name já baixado"; return; }
    echo "  baixando $name"
    curl -fsSL -o "$VIDEOS/$name.mp4" "$url"
}

echo "baixando os vídeos do Pexels"
fetch_pexels video_obra_2 "https://videos.pexels.com/video-files/13921040/13921040-uhd_3840_2160_30fps.mp4"
fetch_pexels video_obra_3 "https://videos.pexels.com/video-files/1197803/1197803-hd_1920_1080_25fps.mp4"
fetch_pexels video_obra_4 "https://videos.pexels.com/video-files/856439/856439-hd_1920_1080_25fps.mp4"

echo "baixando o vídeo do YouTube"
if [ -f "$VIDEOS/video_obra_1.mp4" ]; then
    echo "  video_obra_1 já baixado"
else
    yt-dlp -f 'bestvideo[height<=1080][ext=mp4]/bestvideo[height<=1080]' \
           --merge-output-format mp4 \
           -o "$VIDEOS/video_obra_1.%(ext)s" \
           "https://www.youtube.com/watch?v=SBbBh5xZ1gQ"
fi

echo "extraindo frames a 1 por segundo"
for name in video_obra_1 video_obra_2 video_obra_3 video_obra_4; do
    echo "  $name"
    ffmpeg -v error -y -i "$VIDEOS/$name.mp4" -vf fps=1 "$IMAGES/${name}_%05d.jpg"
done

echo
echo "frames em $IMAGES"
echo "os labels cobrem só as imagens anotadas; as demais podem ser descartadas:"
echo "  para cada $IMAGES/X.jpg sem $OUT/labels/X.txt correspondente"
