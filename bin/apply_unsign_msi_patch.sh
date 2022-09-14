#!/bin/sh
# Copyright (C) 2019 tribe29 GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

signed="$1"
unsigned="$2"
unsigning_patch="$3"
if test ! -f "$signed" || test ! -f "$unsigning_patch"; then
    echo "$0: Can't apply a patch, $signed or $unsigning_patch does not exist." >&2
    exit 1
fi
base64 "$signed" >"$signed".base64
patch "$signed".base64 <"$unsigning_patch"
base64 -d "$signed".base64 >"$unsigned"
rm "$signed".base64
