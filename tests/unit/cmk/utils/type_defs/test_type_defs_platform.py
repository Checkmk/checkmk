#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.cee.bakery.type_defs import AgentPackagePlatform


@pytest.mark.parametrize(
    "platform, tgz_based",
    [
        (AgentPackagePlatform.LINUX_DEB, False),
        (AgentPackagePlatform.LINUX_RPM, False),
        (AgentPackagePlatform.SOLARIS_PKG, False),
        (AgentPackagePlatform.WINDOWS_MSI, False),
        (AgentPackagePlatform.LINUX_TGZ, True),
        (AgentPackagePlatform.SOLARIS_TGZ, True),
        (AgentPackagePlatform.AIX_TGZ, True),
    ],
)
def test_platform_type(platform: AgentPackagePlatform, tgz_based: bool) -> None:
    assert platform.is_tgz_based() == tgz_based
