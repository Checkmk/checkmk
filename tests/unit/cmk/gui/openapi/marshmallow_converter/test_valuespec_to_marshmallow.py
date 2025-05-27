#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest

from tests.unit.cmk.gui.users import create_and_destroy_user

import cmk.utils.paths

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.openapi.marshmallow_converter.valuespec_to_marshmallow import valuespec_to_marshmallow
from cmk.gui.session import UserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.config_domain_name import config_variable_registry


@pytest.fixture(name="fake_user")
def fixture_fake_user() -> Iterator[LoggedInUser]:
    user_dir = cmk.utils.paths.profile_dir / "fake_user"
    user_dir.mkdir(parents=True)

    with create_and_destroy_user(username="fake_user") as user:
        yield LoggedInUser(user[0])


@pytest.mark.usefixtures("request_context")
def test_valuespec_to_marshmallow_all_global_settings(fake_user: LoggedInUser) -> None:
    """
    Test that all global settings can be converted to marshmallow schemas.
    This does not cover the correctness of the generated schemas.
    """
    if fake_user.id:
        with gui_context(), UserContext(fake_user.id):
            for name, config_variable in config_variable_registry.items():
                valuespec_to_marshmallow(config_variable.valuespec(), name=name)
