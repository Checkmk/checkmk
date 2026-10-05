#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# rust_wine_test() prepare hook: import the SQL Server registry entries
# the registry-discovery tests expect (count hardwired in
# expected_count_in_registry, names in expected_instances_in_config) into
# the throwaway Wine prefix, followed by the test sets under
# HKLM\SOFTWARE\checkmk\tests (test_get_instances, test_get_host_tcp_info).
#
# $1: the .reg fixture with the instances (rootpath).
# $2...: the test set .reg files (tests/files/windows-registry).

set -euo pipefail

"$WINE" reg import "$(realpath "$1")"
shift
for reg in "$@"; do
    "$WINE" reg import "$(realpath "$reg")"
done
"$WINE" reg query 'HKLM\SOFTWARE\checkmk\tests\2.5.0\mk-sql\instances' >/dev/null
