#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.plugins.collection.rulesets.bi import _migrate_to_internal_user


@pytest.mark.parametrize(
    "old_rule, expected_rule",
    [
        pytest.param(
            {
                "site": ("url", "http://google.com"),
                "credentials": ("configured", ("un2", ("password", "unnn2"))),
            },
            {
                "site": (
                    "remote",
                    {
                        "credentials": (
                            "configured",
                            {
                                "password": (
                                    "password",
                                    "unnn2",
                                ),
                                "username": "un2",
                            },
                        ),
                        "url": "http://google.com",
                    },
                ),
            },
            id="remote site with credentials",
        ),
        pytest.param(
            {"site": ("url", "https://google.com"), "credentials": ("automation", None)},
            {
                "site": (
                    "remote",
                    {
                        "credentials": (
                            "automation",
                            "automation",
                        ),
                        "url": "https://google.com",
                    },
                )
            },
            id="remote site with automation credentials as tuple",
        ),
        pytest.param(
            {
                "site": "local",
                "credentials": ("configured", ("un1", ("password", "unnn1"))),
            },
            {"site": ("local", None)},
            id="local site with credentials",
        ),
        pytest.param(
            {
                "site": ("local", None),
                "credentials": ("configured", ("un1", ("password", "unnn1"))),
            },
            {"site": ("local", None)},
            id="local site with credentials configured as tuple",
        ),
        pytest.param(
            {"site": "local", "credentials": "automation"},
            {"site": ("local", None)},
            id="local site with automation credentials",
        ),
        pytest.param(
            {
                "credentials": ("automation", None),
                "filter": {"aggr_group_prefix": ["Internet"]},
                "site": ("local", None),
            },
            {
                "filter": {
                    "aggr_group_prefix": [
                        "Internet",
                    ],
                },
                "site": (
                    "local",
                    None,
                ),
            },
            id="local site with automation user",
        ),
        pytest.param(
            {
                "site": ("url", "http://foo.de"),
                "credentials": ("configured", ("user", ("store", "password_1"))),
                "filter": {"aggr_name": ["foobar"]},
            },
            {
                "filter": {
                    "aggr_name": [
                        "foobar",
                    ],
                },
                "site": (
                    "remote",
                    {
                        "credentials": (
                            "configured",
                            {
                                "password": (
                                    "store",
                                    "password_1",
                                ),
                                "username": "user",
                            },
                        ),
                        "url": "http://foo.de",
                    },
                ),
            },
        ),
    ],
)
def test_migrate_to_internal_user(
    old_rule: object,
    expected_rule: Mapping[str, object],
) -> None:
    assert _migrate_to_internal_user(old_rule) == expected_rule
