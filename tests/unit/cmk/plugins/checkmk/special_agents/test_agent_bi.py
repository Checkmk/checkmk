#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.ccc.user import UserId

from cmk.utils.local_secrets import AutomationUserSecret

from cmk.plugins.checkmk.special_agents.agent_bi import (
    AgentBiAutomationUserAuthentication,
    AgentBiConfig,
    AgentBiUserAuthentication,
    AggregationRawdataGenerator,
    merge_config,
)


class TestAggregationRawdataGeneratorLocal:
    @pytest.mark.parametrize(
        [
            "config",
            "expected_username",
            "expected_site_url",
        ],
        [
            pytest.param(
                AgentBiConfig(
                    site_url=None,
                    authentication=None,
                ),
                "internal",
                "http://localhost:5002/NO_SITE",
            ),
        ],
    )
    def test_init(
        self,
        mocker: MockerFixture,
        config: AgentBiConfig,
        expected_username: str,
        expected_site_url: str,
    ) -> None:
        mocker.patch(
            "cmk.utils.password_store._pwstore.load",
            return_value={
                "the_dude_secret": "white_russian",
            },
        )
        mocker.patch("cmk.ccc.site.get_apache_port", return_value=5002)

        secret = AutomationUserSecret(UserId(expected_username))
        secret.path.parent.mkdir(parents=True, exist_ok=True)
        secret.save("lala")

        agg_gen = AggregationRawdataGenerator(config)
        assert "InternalToken" in agg_gen._get_authentication_token()
        assert agg_gen._config == config
        assert agg_gen._site_url == expected_site_url


def _create_automation_user_secret(username: UserId) -> None:
    secret = AutomationUserSecret(username)
    secret.path.parent.mkdir(parents=True, exist_ok=True)
    secret.save("lala")


class TestAggregationRawdataGenerator:
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
                    site_url="http://somewhere:3000/some_site",
                    authentication=AgentBiAutomationUserAuthentication(
                        username="automation",
                    ),
                ),
                "automation",
                "Ischbinwischtisch",
                "http://somewhere:3000/some_site",
                id="standard_automation_user",
            ),
            pytest.param(
                AgentBiConfig(
                    site_url="http://somewhere:3000/some_site",
                    authentication=AgentBiUserAuthentication(
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

        if expected_username == "automation":
            secret = AutomationUserSecret(UserId(expected_username))
            secret.path.parent.mkdir(parents=True, exist_ok=True)
            secret.save("Ischbinwischtisch")

        agg_gen = AggregationRawdataGenerator(config)
        assert (
            agg_gen._get_authentication_token() == f"Bearer {expected_username} {expected_password}"
        )
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
                {
                    "authentication": {
                        "username": "user",
                        "password_store_path": "/bar",
                        "password_store_identifier": "foo",
                    }
                },
                {
                    "authentication": {
                        "username": "user",
                        "password_store_path": "/foo",
                        "password_store_identifier": "bar",
                    }
                },
                {},
                {
                    "authentication": {
                        "username": "user",
                        "password_store_path": "/path",
                        "password_store_identifier": "id",
                    }
                },
            ]
        ],
    )
    assert merged_configs[0].authentication is None
    assert merged_configs[1].authentication is None

    assert merged_configs[2].authentication is not None
    if isinstance(merged_configs[2].authentication, AgentBiUserAuthentication):
        assert merged_configs[2].authentication.password_store_path == Path("/bar")
        assert merged_configs[2].authentication.password_store_identifier == "foo"

    assert merged_configs[3].authentication is not None
    if isinstance(merged_configs[3].authentication, AgentBiUserAuthentication):
        assert merged_configs[3].authentication.password_store_path == Path("/foo")
        assert merged_configs[3].authentication.password_store_identifier == "bar"

    assert merged_configs[4].authentication is None

    assert merged_configs[5].authentication is not None
    if isinstance(merged_configs[5].authentication, AgentBiUserAuthentication):
        assert merged_configs[5].authentication.password_store_path == Path("/path")
        assert merged_configs[5].authentication.password_store_identifier == "id"
