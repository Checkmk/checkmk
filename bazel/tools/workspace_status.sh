#!/bin/bash
set -e

# A stable identifier: commit hash
echo "STABLE_GIT_COMMIT $(git rev-parse HEAD)"

# Volatile: current build timestamp in ISO 8601 format (for OCI image metadata)
echo "BUILD_TIMESTAMP_ISO $(date -u +%Y-%m-%dT%H:%M:%SZ)"
