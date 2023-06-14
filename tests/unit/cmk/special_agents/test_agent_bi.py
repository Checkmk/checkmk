#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest
from pytest_mock import MockerFixture

from tests.testlib.users import create_and_destroy_user

# The test below executes the special agent and queries a mocked REST API endpoint. Some of the
# action plugin tests require an initialized UI context. This is done by referencing the ui_context
# fixture which makes an initialized context available outside of tests.unit.cmk.gui package.
# However, seems we need to import the fixtures referenced by the ui_context fixture to make it
# work.
from tests.unit.cmk.gui.conftest import (  # noqa: F401 # pylint: disable=unused-import
    load_config,
    load_plugins,
    ui_context,
)

from cmk.special_agents.agent_bi import AggregationRawdataGenerator


class TestAggregationRawdataGenerator:
    @pytest.mark.usefixtures("ui_context")
    @pytest.mark.parametrize(
        [
            "config",
            "expected_username",
            "expected_password",
            "expected_site_url",
        ],
        [
            pytest.param(
                {
                    "site": "local",
                    "credentials": "automation",
                },
                "automation",
                "Ischbinwischtisch",
                "http://localhost:5002/NO_SITE",
                id="standard_automation_user",
            ),
            pytest.param(
                {
                    "site": (
                        "url",
                        "http://somewhere:3000/some_site",
                    ),
                    "credentials": (
                        "configured",
                        (
                            "the_dude",
                            (
                                "password",
                                "white_russian",
                            ),
                        ),
                    ),
                },
                "the_dude",
                "white_russian",
                "http://somewhere:3000/some_site",
                id="other_automation_user_explicit_password",
            ),
            pytest.param(
                {
                    "site": "local",
                    "credentials": (
                        "configured",
                        (
                            "the_dude",
                            (
                                "store",
                                "the_dude_secret",
                            ),
                        ),
                    ),
                },
                "the_dude",
                "white_russian",
                "http://localhost:5002/NO_SITE",
                id="other_automation_user_password_store",
            ),
        ],
    )
    def test_init(
        self,
        mocker: MockerFixture,
        config: Mapping[str, Any],
        expected_username: str,
        expected_password: str,
        expected_site_url: str,
    ) -> None:
        mocker.patch(
            "cmk.utils.password_store.load",
            return_value={
                "the_dude_secret": "white_russian",
            },
        )
        with create_and_destroy_user(
            automation=True,
            role="admin",
            username=expected_username,
        ):
            agg_gen = AggregationRawdataGenerator(config)
        assert agg_gen._config == config
        assert agg_gen._username == expected_username
        assert agg_gen._secret == expected_password
        assert agg_gen._site_url == expected_site_url
