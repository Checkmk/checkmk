#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.oracle.agent_based.libinstance import Instance


def test_insance_model_accepts_empty_strings_as_none():
    instance = Instance.model_validate(
        {
            # mandatory fields:
            "sid": "ut_sid",
            "version": "ut_version",
            "openmode": "ut_openmode",
            "logins": "ut_logins",
            # optional field:
            "ptotal_size": "",
        }
    )
    assert instance.ptotal_size is None
