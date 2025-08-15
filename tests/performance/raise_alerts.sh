#!/usr/bin/env bash
_GIT_ROOT=$(git rev-parse --show-toplevel)
find "${_GIT_ROOT}/results/performance" -mindepth 1 -maxdepth 1 -type d | sort | tail -n5 | xargs "${_GIT_ROOT}/tests/performance/perftest_plot.py" "$@"
