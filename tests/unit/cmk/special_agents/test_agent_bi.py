#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

# The test below executes the special agent and queries a mocked REST API endpoint. Some of the
# action plug-in tests require an initialized UI context. This is done by referencing the ui_context
# fixture which makes an initialized context available outside of tests.unit.cmk.gui package.
# However, seems we need to import the fixtures referenced by the ui_context fixture to make it
# work.
from tests.unit.cmk.gui.conftest import (  # noqa: F401
    load_config,
    load_plugins,
    ui_context,
)
from tests.unit.cmk.gui.users import create_and_destroy_user

from cmk.special_agents.agent_bi import (
    AgentBiAuthentication,
    AgentBiConfig,
    AggregationRawdataGenerator,
    merge_config,
)


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
                AgentBiConfig(
                    site_url=None,
                    authentication=None,
                ),
                "automation",
                "Ischbinwischtisch",
                "http://localhost:5002/NO_SITE",
                id="standard_automation_user",
            ),
            pytest.param(
                AgentBiConfig(
                    site_url="http://somewhere:3000/some_site",
                    authentication=AgentBiAuthentication(
                        username="the_dude",
                        password_store_path=Path("/mocked/away"),
                        password_store_identifier="the_dude_secret",
                    ),
                ),
                "the_dude",
                "white_russian",
                "http://somewhere:3000/some_site",
                id="other_automation_user_explicit_password",
            ),
            pytest.param(
                AgentBiConfig(
                    site_url=None,
                    authentication=AgentBiAuthentication(
                        username="the_dude",
                        password_store_path=Path("/mocked/away"),
                        password_store_identifier="the_dude_secret",
                    ),
                ),
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
        config: AgentBiConfig,
        expected_username: str,
        expected_password: str,
        expected_site_url: str,
    ) -> None:
        mocker.patch(
            "cmk.utils.password_store._pwstore.load",
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
            assert agg_gen._get_bearer_token() == f"Bearer {expected_username} {expected_password}"
        assert agg_gen._config == config
        assert agg_gen._site_url == expected_site_url


def test_merge_config() -> None:
    merged_configs = merge_config(
        ["nosecret", "nosecret", "foo:/bar", "bar:/foo", "nosecret", "id:/path"],
        [
            json.dumps(c)
            for c in [
                {},
                {},
                {"authentication": {"username": "user"}},
                {"authentication": {"username": "user"}},
                {},
                {"authentication": {"username": "user"}},
            ]
        ],
    )
    assert merged_configs[0].authentication is None
    assert merged_configs[1].authentication is None

    assert merged_configs[2].authentication is not None
    assert merged_configs[2].authentication.password_store_path == Path("/bar")
    assert merged_configs[2].authentication.password_store_identifier == "foo"

    assert merged_configs[3].authentication is not None
    assert merged_configs[3].authentication.password_store_path == Path("/foo")
    assert merged_configs[3].authentication.password_store_identifier == "bar"

    assert merged_configs[4].authentication is None

    assert merged_configs[5].authentication is not None
    assert merged_configs[5].authentication.password_store_path == Path("/path")
    assert merged_configs[5].authentication.password_store_identifier == "id"
