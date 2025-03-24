#!/bin/bash
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -d, --execution_logs_root      Directory containing the Bazel execution logs (default: current directory)"
    echo "  -p, --bazel_log_file_pattern   glob pattern of log files in execution_logs_root (default deps_install.json)"
    echo "  -s, --summary_file    File to write the summary JSON to (default: summary.json)"
    echo "  -t, --distro          Distro name or identifier (default: unset)"
    echo "  -c, --cachehit_csv File to append the cache hits percentage to (default: cache.csv)"
    echo "  -h, --help            Display this help message and exit"
}

# Default values
execution_logs_root=$(pwd)
summary_file="summary.json"
distro="default distro value"
cachehit_csv="cache.csv"
bazel_log_file_pattern="deps_install.json"

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -d | --execution_logs_root)
            execution_logs_root="$2"
            shift
            ;;
        -p | --bazel_log_file_pattern)
            bazel_log_file_pattern="$2"
            shift
            ;;
        -s | --summary_file)
            summary_file="$2"
            shift
            ;;
        -t | --distro)
            distro="$2"
            shift
            ;;
        -c | --cachehit_csv)
            cachehit_csv="$2"
            shift
            ;;
        -h | --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown parameter passed: $1"
            show_help
            exit 1
            ;;
    esac
    shift
done

# Validate files
if [[ ! -d "$execution_logs_root" ]]; then
    echo "Error: Directory $execution_logs_root does not exist."
    exit 1
fi

query='[ .[] | {
  targetLabel: .targetLabel ,
  cacheHit: (.cacheHit // false),
  cacheable: (.cacheable // false),
  remoteable: (.remoteable // false)
}] | {
  overallTargets: length,
  cacheHits: map(select(.cacheHit == true)) | length,
  percentRemoteCacheHits: ((map(select(.cacheHit == true)) | length) / (length | select(. != 0)) * 100 | round ),
  targetsWithMissedCache: map(select(.cacheHit == false) | .targetLabel),
  numberUncacheableTargets: map(select(.cacheable == false)) | length,
  numberRemotableTargets: map(select(.remoteable == true)) | length,
}'

# we explicitely want globing here!
# shellcheck disable=SC2086
jq -sc "$query" ${execution_logs_root}/${bazel_log_file_pattern} >"${summary_file}"
echo "${distro}" >"${cachehit_csv}"
jq .percentRemoteCacheHits "${summary_file}" >>"${cachehit_csv}"
