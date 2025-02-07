#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.type_defs import GroupSpec
from cmk.gui.views.layout.layouts import get_group_spec


@pytest.mark.parametrize(
    "group_spec, expected_group_spec, service_name",
    [
        pytest.param(
            GroupSpec(
                title="Hardware",
                pattern="(?i:cpu)|(?i:interface).*",
                min_items=2,
            ),
            GroupSpec(
                title="Hardware",
                pattern="(?i:cpu)|(?i:interface).*",
                min_items=2,
            ),
            "Interface 1",
            id="non-capturing groups case 1 (SUP-19435)",
        ),
        pytest.param(
            GroupSpec(
                title="Hardware",
                pattern="(?i:cpu)|(?i:interface).*",
                min_items=2,
            ),
            GroupSpec(
                title="Hardware",
                pattern="(?i:cpu)|(?i:interface).*",
                min_items=2,
            ),
            "CPU load",
            id="non-capturing groups case 2 (SUP-19435)",
        ),
        pytest.param(
            GroupSpec(
                title="CPU",
                pattern="(?!.*(CPU)).*",
                min_items=2,
            ),
            GroupSpec(
                title="CPU",
                pattern="(?!.*(CPU)).*",
                min_items=2,
            ),
            "CPU load",
            id="non-capturing groups case 3 (SUP-21609)",
        ),
        pytest.param(
            GroupSpec(
                title=r"Oracle instance \1",
                pattern="ORA ([A-Za-z0-9]+).*",
                min_items=2,
            ),
            GroupSpec(
                title="Oracle instance 1337",
                pattern="ORA ([A-Za-z0-9]+).*",
                min_items=2,
            ),
            "ORA 1337",
            id="match group replacement (SUP-13124)",
        ),
        pytest.param(
            GroupSpec(
                title="LocalChecks",
                pattern="local_",
                min_items=2,
            ),
            GroupSpec(
                title="LocalChecks",
                pattern="local_",
                min_items=2,
            ),
            r"local_\PTest",
            id=r"Bad escape \P (SUP-14585)",
        ),
        pytest.param(
            GroupSpec(
                title=r"LocalChecks \1",
                pattern="local_(.*)",
                min_items=2,
            ),
            GroupSpec(
                title=r"LocalChecks \PTest",
                pattern="local_(.*)",
                min_items=2,
            ),
            r"local_\PTest",
            id=r"Bad escape \P (SUP-14585)",
        ),
        pytest.param(
            GroupSpec(
                title=r"Foo \1 Bar \2",
                pattern=r"my_(\d+)_services_(\d+)",
                min_items=2,
            ),
            GroupSpec(
                title=r"Foo 10 Bar 20",
                pattern=r"my_(\d+)_services_(\d+)",
                min_items=2,
            ),
            "my_10_services_20",
            id="two match groups replacement",
        ),
    ],
)
def test_get_group_spec(
    group_spec: GroupSpec, expected_group_spec: GroupSpec, service_name: str
) -> None:
    assert get_group_spec(group_spec, service_name) == expected_group_spec
