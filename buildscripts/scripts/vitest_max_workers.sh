#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Print how many CPUs this container may actually use, for sizing test worker
# pools. nproc and os.availableParallelism() report what the OS advertises and
# ignore the cgroup quota that really bounds us. Prints nothing when there is no
# quota to honour, which leaves the caller on its own default.

set -euo pipefail

cpu_max=/sys/fs/cgroup/cpu.max

[[ -r ${cpu_max} ]] || exit 0
read -r quota period <"${cpu_max}" || exit 0
[[ ${quota} =~ ^[0-9]+$ ]] || exit 0
[[ ${period} =~ ^[0-9]+$ ]] && ((period > 0)) || exit 0

echo $((quota / period))
