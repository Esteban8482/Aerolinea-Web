#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -c 'import sys; assert sys.platform == "linux" and sys.version_info[:3] == (3, 13, 16), "Resolver en Linux con Python 3.13.16"'
export CUSTOM_COMPILE_COMMAND="bash scripts/compile_requirements.sh"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/tmp/aerolinea-pip-cache}"
export PIP_TOOLS_CACHE_DIR="${PIP_TOOLS_CACHE_DIR:-/tmp/aerolinea-pip-tools-cache}"
for group in tools base development production; do
    python -m piptools compile --resolver=backtracking --generate-hashes \
        --allow-unsafe --strip-extras --no-emit-index-url --no-emit-trusted-host \
        --output-file="requirements/${group}.txt" "requirements/${group}.in"
done
