#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# rust_wine_test() prepare hook: the factory-runtime detection test
# (setup::tests::test_detect_factory_runtime) points its runtime env var
# at <cwd>/runtimes (its base dir falls back to the cwd with MK_CONFDIR
# unset) and expects to find runtimes/plugins/libexec/mk-oracle-v2/oic there;
# give it a directory to find in the scratch cwd.

set -euo pipefail

mkdir -p "${SCRATCH}/runtimes/plugins/libexec/mk-oracle-v2/oic"
