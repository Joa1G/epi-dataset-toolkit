#!/usr/bin/env bash
#
# Monta os assets do release em dist/.
#
# Dois pacotes e não um, porque as fontes têm licenças diferentes (ver
# SOURCES.md): as anotações são trabalho próprio e vão inteiras; as imagens só
# saem daqui quando a licença do vídeo de origem permite redistribuição.
#
# Uso: ./scripts/build-release.sh [pasta-do-dataset]   (padrão: data)

set -euo pipefail

DATA="${1:-data}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

command -v zip >/dev/null || { echo "falta zip" >&2; exit 1; }
[ -d "$DATA/labels" ] || { echo "não achei $DATA/labels" >&2; exit 1; }

rm -rf "$DIST"
mkdir -p "$DIST"

# --- anotações: tudo, é trabalho próprio ---
mkdir -p "$STAGE/labels-pkg/labels"
cp "$DATA"/labels/*.txt "$STAGE/labels-pkg/labels/"
cp "$DATA/data.yaml" "$ROOT/ANNOTATION_GUIDE.md" "$ROOT/SOURCES.md" \
   "$ROOT/extract.sh" "$STAGE/labels-pkg/"
# O README do pacote é outro que o do repositório: quem baixa o zip precisa
# saber por que faltam imagens antes de achar que o dataset veio quebrado.
cp "$ROOT/release-README.md" "$STAGE/labels-pkg/README.md"
(cd "$STAGE/labels-pkg" && zip -qr "$DIST/labels.zip" .)

# --- imagens: só as dos vídeos sob Pexels License ---
# video_obra_1 é do YouTube sob licença padrão e fica de fora; o extract.sh
# reconstrói esses frames a partir da fonte.
mkdir -p "$STAGE/images-pkg/images"
cp "$DATA"/images/video_obra_[234]_*.jpg "$STAGE/images-pkg/images/"
(cd "$STAGE/images-pkg" && zip -qr "$DIST/images-pexels.zip" .)

echo "montado em $DIST:"
for asset in "$DIST"/*.zip; do
    printf "  %-22s %6s  %s arquivos\n" \
        "$(basename "$asset")" \
        "$(du -h "$asset" | cut -f1)" \
        "$(unzip -l "$asset" | tail -1 | awk '{print $2}')"
done
