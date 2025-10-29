#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def test_special_agent_importable() -> None:
    import cmk.plugins.netapp.special_agent.agent_netapp_ontap  # noqa: F401

    assert True
