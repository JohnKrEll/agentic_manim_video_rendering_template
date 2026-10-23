#!/usr/bin/env bash
# Sets up the tools the pipeline needs, in .venv/ next to this file.
#
#   ./setup.sh               Python packages (Manim, faster-whisper)
#   ./setup.sh --with-model  also download the Whisper model now (~3 GB)
#   ./setup.sh --link PATH   reuse an existing venv that already has Manim
set -euo pipefail

cd "$(dirname "$0")"

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; exit 1; }

echo "System tools"
command -v ffmpeg  >/dev/null && ok "ffmpeg"  || fail "ffmpeg is missing (Fedora: sudo dnf install ffmpeg, Ubuntu: sudo apt install ffmpeg, macOS: brew install ffmpeg)"
command -v ffprobe >/dev/null && ok "ffprobe" || fail "ffprobe is missing (it comes with ffmpeg)"

# A .venv that is a link to a venv that no longer exists (e.g. after copying
# the template to another machine) is removed so a fresh one can be made.
if [ -L .venv ] && [ ! -e .venv ]; then
    warn "removing broken .venv link"
    rm .venv
fi

if [ "${1:-}" = "--link" ]; then
    [ -x "${2:-}/bin/python" ] || fail "no Python at ${2:-}/bin/python"
    ln -sfn "$(cd "$2" && pwd)" .venv
    ok ".venv → $2"
fi

echo "Python environment"
if [ ! -x .venv/bin/python ]; then
    if command -v uv >/dev/null; then
        uv venv --python 3.12 .venv >/dev/null
    else
        PY=$(command -v python3.12 || command -v python3.13 || command -v python3.11 || command -v python3)
        "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 11))' || fail "Python 3.11+ is needed (found $("$PY" --version))"
        "$PY" -m venv .venv
    fi
    ok "created .venv"
fi
if command -v uv >/dev/null; then
    uv pip install --python .venv/bin/python -q -r requirements.txt
else
    .venv/bin/python -m pip install -q -r requirements.txt
fi
ok "$(.venv/bin/python -c 'import manim, faster_whisper; print(f"manim {manim.__version__}, faster-whisper {faster_whisper.__version__}")')"

echo "Fonts"
.venv/bin/python - <<'EOF'
import sys
sys.path.insert(0, "design")
import theme
from manimpango import list_fonts
have = set(list_fonts())
for kind, wanted in (("text", theme.SANS_FONTS), ("code", theme.MONO_FONTS)):
    found = next((f for f in wanted if f in have), None)
    if found == wanted[0]:
        print(f"  \033[32m✓\033[0m {kind}: {found}")
    elif found:
        print(f"  \033[33m!\033[0m {kind}: {found} (install {wanted[0]} for the intended look)")
    else:
        print(f"  \033[31m✗\033[0m {kind}: none of {', '.join(wanted)} is installed")
EOF

if [ "${1:-}" = "--with-model" ]; then
    echo "Whisper model"
    MODEL=$(.venv/bin/python -c 'import tomllib; print(tomllib.load(open("project.toml","rb")).get("whisper_model","large-v3"))')
    .venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('$MODEL', device='cpu', compute_type='int8')"
    ok "$MODEL downloaded"
else
    warn "the Whisper model downloads on first use (or run ./setup.sh --with-model)"
fi

echo
echo "Ready. Try: ./pipeline status"
