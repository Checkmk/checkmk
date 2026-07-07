#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# rust_wine_test() prepare hook: import the SQL Server registry entries
# the registry-discovery tests expect (count hardwired in
# expected_count_in_registry, names in expected_instances_in_config) into
# the throwaway Wine prefix.
#
# $1: the .reg fixture (rootpath).

set -euo pipefail

"$WINE" regedit /s "$(realpath "$1")"
# regedit /s can exit 0 on a failed import; fail crisply here instead of
# as "expected 3, got 0" discovery failures later.
"$WINE" reg query 'HKLM\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL' >/dev/null
