#!/usr/bin/env bash
# Installs or verifies the two tools this project needs: Blender 4.2 LTS and FFmpeg.
# Works in Git Bash on Windows (also Linux/macOS).  Nothing is installed system-wide:
# missing tools are downloaded once into ./tools/ and reused on later runs.
#
#   bash install.sh          # verify / install
#   source tools/env.sh      # (render.sh does this for you)
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
TOOLS="$ROOT/tools"
mkdir -p "$TOOLS"

BLENDER_VERSION="4.2.3"
BLENDER_SERIES="4.2"
FFMPEG_URL="https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

say()  { printf '\033[1;36m[install]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[install]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[install] ERROR:\033[0m %s\n' "$*"; exit 1; }

OS="$(uname -s)"
case "$OS" in
  MINGW*|MSYS*|CYGWIN*) PLATFORM=windows; EXE=".exe" ;;
  Linux*)  PLATFORM=linux;  EXE="" ;;
  Darwin*) PLATFORM=macos;  EXE="" ;;
  *) die "unsupported OS: $OS" ;;
esac
say "platform: $PLATFORM ($OS)"

download() {  # url dest
  say "downloading $(basename "$2") ..."
  curl -fL --retry 4 --retry-delay 3 -C - -o "$2.part" "$1" || die "download failed: $1"
  mv "$2.part" "$2"
}

unzip_to() {  # zip dir
  mkdir -p "$2"
  if [ "$PLATFORM" = windows ]; then
    # PowerShell is present on every Windows 10/11; Git Bash's unzip is optional.
    local zw dw
    zw="$(cygpath -w "$1")"; dw="$(cygpath -w "$2")"
    powershell.exe -NoProfile -Command "Expand-Archive -LiteralPath '$zw' -DestinationPath '$dw' -Force" \
      || die "could not extract $1"
  else
    unzip -q -o "$1" -d "$2" || die "could not extract $1"
  fi
}

# ------------------------------------------------------------------ Blender
find_blender() {
  if [ -n "${BLENDER:-}" ] && [ -x "$BLENDER" ]; then echo "$BLENDER"; return; fi
  local c
  for c in "$TOOLS"/blender-*/blender"$EXE" \
           "/c/Program Files/Blender Foundation/Blender $BLENDER_SERIES/blender.exe" \
           "/c/Program Files/Blender Foundation/Blender 4.5/blender.exe" \
           "/c/Program Files/Blender Foundation/Blender 4.4/blender.exe" \
           "/c/Program Files/Blender Foundation/Blender 4.3/blender.exe" \
           "/Applications/Blender.app/Contents/MacOS/Blender"; do
    [ -x "$c" ] && { echo "$c"; return; }
  done
  command -v blender >/dev/null 2>&1 && { command -v blender; return; }
  echo ""
}

blender_ok() {  # requires >= 4.2
  local v
  v="$("$1" -b --factory-startup --python-expr "import bpy;print('BLENDER_VERSION', bpy.app.version[0], bpy.app.version[1])" 2>/dev/null || true)"
  v="$(printf '%s\n' "$v" | grep BLENDER_VERSION | head -n 1 || true)"
  set -- $v
  [ -n "${2:-}" ] && { [ "$2" -gt 4 ] || { [ "$2" -eq 4 ] && [ "$3" -ge 2 ]; }; }
}

BLENDER_BIN="$(find_blender)"
if [ -n "$BLENDER_BIN" ] && blender_ok "$BLENDER_BIN"; then
  say "Blender found: $BLENDER_BIN"
else
  [ -n "$BLENDER_BIN" ] && warn "Blender at $BLENDER_BIN is older than 4.2 - installing a portable 4.2 LTS"
  case "$PLATFORM" in
    windows) PKG="blender-$BLENDER_VERSION-windows-x64.zip" ;;
    linux)   PKG="blender-$BLENDER_VERSION-linux-x64.tar.xz" ;;
    macos)   die "please install Blender 4.2+ from https://www.blender.org/download/ and re-run" ;;
  esac
  [ -f "$TOOLS/$PKG" ] || download "https://download.blender.org/release/Blender$BLENDER_SERIES/$PKG" "$TOOLS/$PKG"
  say "extracting Blender (about 1 GB, one time only) ..."
  if [ "$PLATFORM" = windows ]; then unzip_to "$TOOLS/$PKG" "$TOOLS"; else tar -xf "$TOOLS/$PKG" -C "$TOOLS"; fi
  rm -f "$TOOLS/$PKG"
  BLENDER_BIN="$(find_blender)"
  [ -n "$BLENDER_BIN" ] && blender_ok "$BLENDER_BIN" || die "Blender install failed - see README troubleshooting"
  say "Blender installed: $BLENDER_BIN"
fi

# ------------------------------------------------------------------ FFmpeg
find_ffmpeg() {
  if [ -n "${FFMPEG:-}" ] && [ -x "$FFMPEG" ]; then echo "$FFMPEG"; return; fi
  local c
  for c in "$TOOLS"/ffmpeg-*/bin/ffmpeg"$EXE"; do [ -x "$c" ] && { echo "$c"; return; }; done
  command -v ffmpeg >/dev/null 2>&1 && { command -v ffmpeg; return; }
  echo ""
}
FFMPEG_BIN="$(find_ffmpeg)"
if [ -z "$FFMPEG_BIN" ]; then
  if [ "$PLATFORM" = windows ]; then
    download "$FFMPEG_URL" "$TOOLS/ffmpeg.zip"
    unzip_to "$TOOLS/ffmpeg.zip" "$TOOLS"
    rm -f "$TOOLS/ffmpeg.zip"
    FFMPEG_BIN="$(find_ffmpeg)"
  else
    die "ffmpeg not found - install it with your package manager (apt install ffmpeg / brew install ffmpeg)"
  fi
fi
[ -n "$FFMPEG_BIN" ] || die "ffmpeg install failed"
FFPROBE_BIN="$(dirname "$FFMPEG_BIN")/ffprobe$EXE"
[ -x "$FFPROBE_BIN" ] || FFPROBE_BIN="$(command -v ffprobe || true)"
[ -n "$FFPROBE_BIN" ] || die "ffprobe not found next to ffmpeg"
ENCODERS="$("$FFMPEG_BIN" -hide_banner -encoders 2>/dev/null || true)"
case "$ENCODERS" in *libx264*) ;; *) die "this ffmpeg build has no libx264 encoder" ;; esac
say "FFmpeg found: $FFMPEG_BIN ($("$FFMPEG_BIN" -version | head -1 | cut -d' ' -f3))"

# ------------------------------------------------------------------ numpy inside Blender
NP="$("$BLENDER_BIN" -b --factory-startup --python-expr "import numpy;print('NUMPY_OK', numpy.__version__)" 2>/dev/null || true)"
case "$NP" in *NUMPY_OK*) ;; *) die "Blender's bundled Python has no numpy (unexpected) - reinstall Blender 4.2" ;; esac
say "Blender Python + numpy OK"

cat > "$TOOLS/env.sh" <<EOF
# generated by install.sh
export BLENDER="$BLENDER_BIN"
export FFMPEG="$FFMPEG_BIN"
export FFPROBE="$FFPROBE_BIN"
EOF
say "all dependencies ready (saved to tools/env.sh)"
