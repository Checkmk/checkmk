#!/bin/sh
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Reason for this no-op: shellcheck disable=... before the first command disables the error for the
# entire script.
:

# Disable unused variable error (needed to keep track of version)
# shellcheck disable=SC2034
CMK_VERSION="2.1.0b7"

su - griduser -c "asmcmd $*"
