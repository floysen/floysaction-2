#!/usr/bin/env bash
# Installs or verifies everything the 3D renderer needs, inside this folder only:
#   Node.js + three.js packages, Python 3.12 (audio + word timing), FFmpeg,
#   and checks for Microsoft Edge / Google Chrome (used to render through your GPU).
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"; TOOLS="$ROOT/tools/bin"; mkdir -p "$TOOLS"
say() { printf '\033[1;36m[install]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[install] ERROR:\033[0m %s\n' "$*"; exit 1; }
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) PLATFORM=windows; EXE=".exe"; VPY=".venv/Scripts/python.exe" ;;
  Linux*) PLATFORM=linux; EXE=""; VPY=".venv/bin/python" ;;
  Darwin*) PLATFORM=macos; EXE=""; VPY=".venv/bin/python" ;;
  *) die "unsupported OS" ;;
esac
download() { say "downloading $(basename "$2") ..."; curl -fL --retry 4 --retry-delay 3 -o "$2.part" "$1" || die "download failed: $1"; mv "$2.part" "$2"; }
unzip_to() {
  mkdir -p "$2"
  if [ "$PLATFORM" = windows ]; then
    powershell.exe -NoProfile -Command "Expand-Archive -LiteralPath '$(cygpath -w "$1")' -DestinationPath '$(cygpath -w "$2")' -Force" || die "could not extract $1"
  else unzip -q -o "$1" -d "$2" || die "could not extract $1"; fi
}

# ---------------- Node.js
NODE_VER="22.12.0"
NODE_BIN=""
for c in "$TOOLS"/node-v*/node"$EXE" "$TOOLS"/node-v*/bin/node; do [ -x "$c" ] && NODE_BIN="$c"; done
if [ -z "$NODE_BIN" ] && command -v node >/dev/null 2>&1; then
  v=$(node -v | tr -d v | cut -d. -f1); [ "$v" -ge 18 ] && NODE_BIN="$(command -v node)"
fi
if [ -z "$NODE_BIN" ]; then
  case "$PLATFORM" in
    windows) download "https://nodejs.org/dist/v$NODE_VER/node-v$NODE_VER-win-x64.zip" "$TOOLS/node.zip"; unzip_to "$TOOLS/node.zip" "$TOOLS"; rm -f "$TOOLS/node.zip"
             NODE_BIN="$TOOLS/node-v$NODE_VER-win-x64/node.exe" ;;
    linux) download "https://nodejs.org/dist/v$NODE_VER/node-v$NODE_VER-linux-x64.tar.xz" "$TOOLS/node.tar.xz"; tar -xf "$TOOLS/node.tar.xz" -C "$TOOLS"; rm -f "$TOOLS/node.tar.xz"
           NODE_BIN="$TOOLS/node-v$NODE_VER-linux-x64/bin/node" ;;
    macos) die "install Node.js 18+ from https://nodejs.org and re-run" ;;
  esac
fi
NODE_DIR="$(dirname "$NODE_BIN")"; export PATH="$NODE_DIR:$PATH"
say "node $("$NODE_BIN" -v)"
if [ ! -f node_modules/three/package.json ] || [ ! -f node_modules/n8ao/package.json ] || [ ! -f node_modules/playwright-core/package.json ]; then
  say "installing three.js packages ..."
  if [ -f "$NODE_DIR/npm.cmd" ]; then "$NODE_DIR/npm.cmd" install --no-audit --no-fund; elif [ -x "$NODE_DIR/npm" ]; then "$NODE_DIR/npm" install --no-audit --no-fund; else npm install --no-audit --no-fund; fi \
    || die "npm install failed"
fi

# ---------------- browser (renders through your GPU)
BROWSER_BIN="${BROWSER:-}"
for c in "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" "/c/Program Files/Microsoft/Edge/Application/msedge.exe" \
         "/c/Program Files/Google/Chrome/Application/chrome.exe" "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
         /usr/bin/google-chrome /usr/bin/chromium /usr/bin/chromium-browser /opt/pw-browsers/chromium-*/chrome-linux/chrome \
         "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
  [ -z "$BROWSER_BIN" ] && [ -x "$c" ] && BROWSER_BIN="$c"
done
[ -n "$BROWSER_BIN" ] || die "Microsoft Edge or Google Chrome is required (Edge is built into Windows 10/11)"
[ "$PLATFORM" = windows ] && BROWSER_BIN="$(cygpath -w "$BROWSER_BIN")"
say "browser: $BROWSER_BIN"

# ---------------- uv + Python (audio mix, word timing)
UV="$(command -v uv || true)"; [ -z "$UV" ] && [ -x "$TOOLS/uv$EXE" ] && UV="$TOOLS/uv$EXE"
if [ -z "$UV" ]; then
  case "$PLATFORM" in
    windows) download "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" "$TOOLS/uv.zip"; unzip_to "$TOOLS/uv.zip" "$TOOLS"; rm -f "$TOOLS/uv.zip" ;;
    linux) download "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz" "$TOOLS/uv.tgz"; tar -xzf "$TOOLS/uv.tgz" -C "$TOOLS" --strip-components=1; rm -f "$TOOLS/uv.tgz" ;;
    macos) die "install uv first: https://docs.astral.sh/uv/" ;;
  esac
  UV="$TOOLS/uv$EXE"
fi
if [ ! -x "$VPY" ] || ! "$VPY" -c "import numpy" >/dev/null 2>&1; then
  say "creating private Python environment ..."
  UV_PYTHON_INSTALL_DIR="$TOOLS/python" "$UV" venv --python 3.12 .venv || die "could not create Python environment"
  "$UV" pip install --python "$VPY" numpy || die "could not install numpy"
fi

# ---------------- FFmpeg
FFMPEG_BIN="${FFMPEG:-}"
[ -z "$FFMPEG_BIN" ] && for c in "$TOOLS"/ffmpeg-*/bin/ffmpeg"$EXE"; do [ -x "$c" ] && FFMPEG_BIN="$c"; done
[ -z "$FFMPEG_BIN" ] && FFMPEG_BIN="$(command -v ffmpeg || true)"
if [ -z "$FFMPEG_BIN" ]; then
  [ "$PLATFORM" = windows ] || die "install ffmpeg (apt install ffmpeg / brew install ffmpeg)"
  download "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" "$TOOLS/ffmpeg.zip"; unzip_to "$TOOLS/ffmpeg.zip" "$TOOLS"; rm -f "$TOOLS/ffmpeg.zip"
  for c in "$TOOLS"/ffmpeg-*/bin/ffmpeg"$EXE"; do [ -x "$c" ] && FFMPEG_BIN="$c"; done
fi
[ -n "$FFMPEG_BIN" ] || die "ffmpeg install failed"
FFPROBE_BIN="$(dirname "$FFMPEG_BIN")/ffprobe$EXE"; [ -x "$FFPROBE_BIN" ] || FFPROBE_BIN="$(command -v ffprobe)"
say "ffmpeg: $FFMPEG_BIN"

cat > tools/env.sh <<EOS
export NODE="$NODE_BIN"
export PATH="$NODE_DIR:\$PATH"
export PY="$ROOT/$VPY"
export UV="$UV"
export BROWSER="$BROWSER_BIN"
export FFMPEG="$FFMPEG_BIN"
export FFPROBE="$FFPROBE_BIN"
EOS
say "all dependencies ready"
