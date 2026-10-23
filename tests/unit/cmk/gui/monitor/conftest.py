#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.ccc.user import UserId
from cmk.gui import login
from cmk.gui.config import Config
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from tests.testlib.unit.gui.users import create_and_destroy_user


@pytest.fixture(name="user_without_permissions")
def fixture_user_without_permissions(load_config: Config) -> Iterator[UserId]:
    with create_and_destroy_user(
        automation=False, role="no_permissions", config=load_config
    ) as created:
        user_id = created[0]
        with login.TransactionIdContext(
            user_id,
            UserPermissions(
                load_config.roles,
                all_permissions(),
                {user_id: ["no_permissions"]},
                [],
            ),
        ):
            yield user_id
