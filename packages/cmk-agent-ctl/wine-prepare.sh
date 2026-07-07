#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# rust_wine_test() prepare hook: stage the cross-built controller where
# the external tests expect it — tests/common/mod.rs derives its path
# from the test's cwd as packages/cmk-agent-ctl/<exe>.
#
# $1: the controller executable (rootpath).

set -euo pipefail

mkdir -p "${SCRATCH}/packages/cmk-agent-ctl"
cp -L "$1" "${SCRATCH}/packages/cmk-agent-ctl/"
