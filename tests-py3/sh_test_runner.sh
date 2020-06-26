#!/usr/bin/env bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

export UNIT_SH_SHUNIT2="./shunit2"
export UNIT_SH_PLUGINS_DIR="../agents/plugins"

for f in $(find ./agent-plugin-unit -name "test*.sh"); do
    $f
done
