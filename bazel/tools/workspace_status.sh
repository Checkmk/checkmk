#!/bin/bash
set -e

# A stable identifier: commit hash
echo "STABLE_GIT_COMMIT $(git rev-parse HEAD)"
