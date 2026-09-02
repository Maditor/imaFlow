#!/bin/bash
# AI Redraw Panel - installer cho macOS
# Cach dung: mo Terminal, cd vao thu muc nay, roi chay: bash install.sh

EXT_NAME="Remini"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)/$EXT_NAME"
DEST_DIR="$HOME/Library/Application Support/Adobe/CEP/extensions/$EXT_NAME"

echo "================================================"
echo "   AI Redraw Panel - Trinh cai dat cho Photoshop"
echo "================================================"
echo

if [ ! -d "$SRC_DIR" ]; then
    echo "[LOI] Khong tim thay thu muc '$EXT_NAME' cung cap voi install.sh"
    exit 1
fi

echo "[1/3] Dang bat che do Debug cho CEP..."
for v in 6 7 8 9 10 11 12; do
    defaults write "com.adobe.CSXS.$v" PlayerDebugMode 1 2>/dev/null
done
echo "      -> Da bat PlayerDebugMode cho CSXS.6 den CSXS.12"

echo
echo "[2/3] Dang sao chep extension..."
mkdir -p "$HOME/Library/Application Support/Adobe/CEP/extensions"
rm -rf "$DEST_DIR"
cp -R "$SRC_DIR" "$DEST_DIR"
echo "      -> Da cai vao: $DEST_DIR"

echo
echo "[3/3] Cai dat hoan tat!"
echo
echo "   Hay KHOI DONG LAI Photoshop, sau do vao:"
echo "   Window > Extensions > AI Redraw Panel"
echo "================================================"
