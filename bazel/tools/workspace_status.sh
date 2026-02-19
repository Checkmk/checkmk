#!/bin/bash
set -e

# A stable identifier: commit hash
echo "STABLE_GIT_COMMIT $(git rev-parse HEAD)"

# Volatile: last git commit timestamp in ISO 8601 format UTC (for OCI image metadata)
echo "BUILD_TIMESTAMP_ISO $(date -u -d @"$(git log -1 --format=%ct HEAD)" +%Y-%m-%dT%H:%M:%SZ)"
