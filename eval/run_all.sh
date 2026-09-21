#!/usr/bin/env bash
# Every committed result, from committed inputs, in order.
#
# This is what the header of each generated file tells the reader to rerun. It
# needs no GPU, no Ollama, no database and no network: `data/runs/` is frozen
# precisely so that the evaluation reruns on any machine with Python.
#
# Rerunning on unchanged inputs rewrites every output identically, so `git
# diff` after a run is the check that nothing drifted.
set -euo pipefail

cd "$(dirname "$0")/.."

uv run python eval/localisation_results.py
uv run python eval/throughput_results.py
uv run python eval/render_macros.py
