#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from http import HTTPStatus
from pathlib import Path

import pydantic
import pytest
import responses

from cmk.product_usage.collectors import agent_updater
from cmk.product_usage.schema import AgentUpdaterData
from cmk.utils.local_secrets import SiteInternalSecret

SITE_ID = "NO_SITE"
APACHE_PORT = 5000
USAGE_URL = (
    f"http://localhost:{APACHE_PORT}/{SITE_ID}"
    "/check_mk/api/internal/domain-types/agent/actions/updater_usage/invoke"
)
COUNTS = {
    "state": "ok",
    "count_hosts_no_updater": 3,
    "count_hosts_controller_only": 97,
    "count_hosts_legacy_only": 5,
    "count_hosts_both_installed_by_controller": 12,
    "count_hosts_both_installed_by_legacy": 1,
}


def test_the_counts_of_the_site_are_collected(
    tmp_path: Path, site_api: responses.RequestsMock
) -> None:
    site_api.get(USAGE_URL, json=COUNTS)

    collected = agent_updater.collect(_site_dir(tmp_path), SITE_ID, _logger())

    assert collected == AgentUpdaterData(
        state="ok",
        count_hosts_no_updater=3,
        count_hosts_controller_only=97,
        count_hosts_legacy_only=5,
        count_hosts_both_installed_by_controller=12,
        count_hosts_both_installed_by_legacy=1,
    )


def test_the_request_holds_the_site_internal_secret(
    tmp_path: Path, site_api: responses.RequestsMock
) -> None:
    """The endpoint answers no other caller, so a request without the secret collects nothing"""
    site_api.get(
        USAGE_URL,
        json=COUNTS,
        match=[
            responses.matchers.header_matcher(
                {"Authorization": f"InternalToken {SiteInternalSecret().secret.b64_str}"}
            )
        ],
    )

    collected = agent_updater.collect(_site_dir(tmp_path), SITE_ID, _logger())

    assert collected is not None


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(HTTPStatus.NOT_FOUND, id="edition without the Agent Bakery"),
        pytest.param(HTTPStatus.NOT_IMPLEMENTED, id="remote site"),
    ],
)
def test_a_site_that_does_not_report_the_usage_collects_nothing(
    tmp_path: Path, site_api: responses.RequestsMock, status: HTTPStatus
) -> None:
    """Only a setup with the Agent Bakery counts this, and only on its central site"""
    site_api.get(USAGE_URL, status=status)

    collected = agent_updater.collect(_site_dir(tmp_path), SITE_ID, _logger())

    assert collected is None


def test_an_answer_that_is_not_the_counts_is_an_error(
    tmp_path: Path, site_api: responses.RequestsMock
) -> None:
    """Half the counts are no measurement, so the collection fails rather than inventing one"""
    site_api.get(USAGE_URL, json={"state": "ok"})

    with pytest.raises(pydantic.ValidationError):
        agent_updater.collect(_site_dir(tmp_path), SITE_ID, _logger())


def _site_dir(tmp_path: Path) -> Path:
    """A site directory holding the Apache port that the collector builds the URL from"""
    site_conf = tmp_path / "etc" / "omd" / "site.conf"
    site_conf.parent.mkdir(parents=True)
    site_conf.write_text(f"CONFIG_APACHE_TCP_PORT='{APACHE_PORT}'\n")
    return tmp_path


def _logger() -> logging.Logger:
    return logging.getLogger(__name__)
