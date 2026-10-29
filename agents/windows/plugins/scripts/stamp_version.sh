#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Sets the CMK_VERSION of Windows agent plugins, in place. The same edits
# `make setversion` (agents/Makefile) applies to the plugins of the package
# builds, for the copies the Bazel build signs and puts into the MSI.
#
# Usage: stamp_version.sh <version> <file>...

set -euo pipefail

version="$1"
shift

# shellcheck disable=SC2016 # $CMK_VERSION is the PowerShell variable, not ours
sed -i \
    -e 's/\$CMK_VERSION = ".*/$CMK_VERSION = "'"${version}"'"\r/' \
    -e 's/^set CMK_VERSION *=".*/set CMK_VERSION="'"${version}"'"\r/' \
    -e 's/^Const CMK_VERSION = ".*/Const CMK_VERSION = "'"${version}"'"\r/' \
    -e 's/\(^[[:space:]]*\)Version: [0-9.a-z-]*/\1Version: '"${version}"'/' \
    "$@"
