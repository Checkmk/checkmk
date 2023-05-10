# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=has-type
# pylint: disable=used-before-assignment

datasource_programs = [
    {
        "condition": {
            "host_folder": "/wato/agent/",
        },
        "value": "cat ~/var/check_mk/agent_output/<HOST>",
    },
] + datasource_programs
