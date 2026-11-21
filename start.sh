#!/usr/bin/env sh
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python не найден. Ubuntu: sudo apt install python3; macOS: brew install python"
    exit 1
fi

exec "$PY" scripts/bootstrap.py "$@"
