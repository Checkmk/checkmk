#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.sites import SiteManagement, validate_new_site_id
from cmk.livestatus_client import (
    NetworkSocketDetails,
    SiteConfiguration,
    SiteConfigurations,
)


def _local_site_config() -> SiteConfiguration:
    return SiteConfiguration(
        id=SiteId("central"),
        alias="Central",
        socket=("local", None),
        disable_wato=False,
        disabled=False,
        insecure=False,
        url_prefix="/central/",
        multisiteurl="",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication=None,
        timeout=5,
        user_login=True,
        proxy=None,
        user_sync="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=True,
    )


def _remote_site_config() -> SiteConfiguration:
    return SiteConfiguration(
        id=SiteId("remote"),
        alias="Remote",
        socket=(
            "tcp",
            NetworkSocketDetails(
                address=("127.0.0.1", 6557),
                tls=("encrypted", {"verify": True}),
            ),
        ),
        disable_wato=True,
        disabled=False,
        insecure=False,
        url_prefix="/remote/",
        multisiteurl="http://remote/check_mk/",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave",
        timeout=5,
        user_login=True,
        proxy=None,
        user_sync="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )


@pytest.mark.parametrize(
    "site_id",
    [
        pytest.param("remote-1", id="dash"),
        pytest.param("1remote", id="leading_digit"),
        pytest.param("a" * 17, id="too_long"),
        pytest.param("sitä", id="non_ascii"),
        pytest.param("remote\n", id="trailing_newline"),
        pytest.param("", id="empty"),
    ],
)
def test_validate_new_site_id_rejects_invalid_site_id(site_id: str) -> None:
    with pytest.raises(MKUserError, match="site id"):
        validate_new_site_id(site_id)


@pytest.mark.parametrize(
    "site_id",
    [
        pytest.param("remote", id="letters"),
        pytest.param("remote_1", id="digits_and_underscore"),
        pytest.param("_r", id="leading_underscore"),
        pytest.param("a" * 16, id="maximum_length"),
    ],
)
def test_validate_new_site_id_accepts_valid_site_id(site_id: str) -> None:
    validate_new_site_id(site_id)


def test_validate_configuration_rejects_invalid_new_site_id(request_context: None) -> None:
    with pytest.raises(MKUserError, match="site id"):
        SiteManagement.validate_configuration(
            SiteId("remote-1"),
            _remote_site_config(),
            SiteConfigurations({SiteId("central"): _local_site_config()}),
        )


def test_validate_configuration_accepts_invalid_site_id_of_existing_connection(
    request_context: None,
) -> None:
    site_id = SiteId("remote-1")
    SiteManagement.validate_configuration(
        site_id,
        _remote_site_config(),
        SiteConfigurations(
            {SiteId("central"): _local_site_config(), site_id: _remote_site_config()}
        ),
    )
