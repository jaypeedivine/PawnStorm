#!/bin/bash
set -e

echo "=== PawnStorm APK Builder ==="
echo ""

sudo apt-get update -qq
sudo apt-get install -y -qq \
    build-essential ccache git zlib1g-dev libncurses5-dev \
    libffi-dev libssl-dev libtool pkg-config autoconf automake \
    cmake unzip zip openjdk-17-jdk-headless lld 2>&1 | tail -3

pip3 install --user --break-system-packages buildozer cython python-for-android 2>&1 | tail -3

BUILDDIR="/tmp/pawnstorm_build"
mkdir -p "$BUILDDIR"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR"/*.py "$BUILDDIR/"
cp "$SCRIPT_DIR"/buildozer.spec "$BUILDDIR/"
cp "$SCRIPT_DIR"/pawnstorm_icon.png "$BUILDDIR/"
cp -r "$SCRIPT_DIR"/fonts "$BUILDDIR/"

cd "$BUILDDIR"
echo ""
echo "Building APK (first build downloads ~3GB SDK/NDK, takes 15-30 min)..."
echo ""
python3 -m buildozer android debug 2>&1 | tee build.log | tail -20

APK=$(find "$BUILDDIR/bin" -name "*.apk" 2>/dev/null | head -1)
if [ -n "$APK" ]; then
    cp "$APK" "$SCRIPT_DIR/PawnStorm.apk"
    echo ""
    echo "=== SUCCESS ==="
    echo "APK saved to: $SCRIPT_DIR/PawnStorm.apk"
    echo "Transfer to your phone and install (enable 'Unknown Sources' in settings)"
else
    echo ""
    echo "=== BUILD FAILED ==="
    echo "Check build.log at: $BUILDDIR/build.log"
fi
