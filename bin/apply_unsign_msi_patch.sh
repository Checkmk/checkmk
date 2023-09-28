#!/bin/sh
# Copyright (C) 2019 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

signed="$1"
unsigned="$2"
unsign_msi_patch="$3"
if test ! -f "$signed" || test ! -f "$unsign_msi_patch"; then
    echo "$0: Can't apply a patch, $signed or $unsign_msi_patch does not exist." >&2
    exit 1
fi
raw_base64="$unsigned".raw.base64
base64 "$signed" >"$raw_base64"
patch "$raw_base64" <"$unsign_msi_patch"
base64 -d "$raw_base64" >"$unsigned"
rm "$raw_base64"
