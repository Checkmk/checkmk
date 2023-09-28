#!/bin/sh
# Copyright (C) 2019 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

signed="$1"
unsigned="$2"
if test ! -f "$signed" || test ! -f "$unsigned"; then
    echo "$0: Can't make a patch, $signed or $unsigned does not exist." >&2
    exit 1
fi
base64 "$signed" >"$signed".base64
base64 "$unsigned" >"$unsigned".base64
diff -Naur "$signed".base64 "$unsigned".base64 >"$3"
rm "$signed".base64
rm "$unsigned".base64
