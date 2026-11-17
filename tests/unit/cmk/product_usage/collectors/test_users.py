#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.product_usage.collectors.users as users_collector
from cmk.product_usage.schema import UserCount
from tests.unit.cmk.product_usage.user_store import write_user_store

BUSINESS = UserCount(business=1, non_business=0)
NON_BUSINESS = UserCount(business=0, non_business=1)


@pytest.mark.parametrize(
    "user_id, expected",
    [
        pytest.param("jane@acme.com", BUSINESS, id="business domain"),
        pytest.param("jane@gmail.com", NON_BUSINESS, id="free-mail domain"),
        pytest.param("jane@GMX.DE", NON_BUSINESS, id="free-mail domain in upper case"),
        pytest.param("jane@mail.gmx.de", NON_BUSINESS, id="subdomain of a free-mail domain"),
        pytest.param("jane@notgmx.de", BUSINESS, id="domain ending in a free-mail domain"),
    ],
)
def test_cognito_user_is_counted_by_the_domain_of_their_address(
    tmp_path: Path, user_id: str, expected: UserCount
) -> None:
    write_user_store(tmp_path, {user_id: {"connector": "cognito"}})

    assert users_collector.collect(tmp_path) == expected


def test_users_of_other_connectors_are_not_counted(tmp_path: Path) -> None:
    write_user_store(
        tmp_path,
        {"jane@acme.com": {"connector": "htpasswd"}, "john@acme.com": {}},
    )

    assert users_collector.collect(tmp_path) == UserCount(business=0, non_business=0)
