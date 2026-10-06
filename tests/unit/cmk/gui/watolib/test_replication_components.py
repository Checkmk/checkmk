#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.watolib import activate_changes
from cmk.gui.watolib.config_sync import replication_path_registry
from cmk.livestatus_client import SiteConfiguration

_EC_IDENTS = {"mkeventd", "mkeventd_mkp"}
_MKP_IDENTS = {"local", "mkps", "mkps_avail", "mkps_disabled"}


def _default_site_config() -> SiteConfiguration:
    return SiteConfiguration(
        id=SiteId("mysite"),
        alias="Site mysite",
        socket=("local", None),
        disable_wato=True,
        disabled=False,
        insecure=False,
        url_prefix="/mysite/",
        multisiteurl="",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave",
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )


@pytest.mark.parametrize("replicate_ec", [None, True, False])
@pytest.mark.parametrize("replicate_mkps", [None, True, False])
@pytest.mark.usefixtures("request_context")
def test_get_replication_components(replicate_ec: bool | None, replicate_mkps: bool | None) -> None:
    site_config = _default_site_config()

    if replicate_ec is not None:
        site_config["replicate_ec"] = replicate_ec
    if replicate_mkps is not None:
        site_config["replicate_mkps"] = replicate_mkps

    # otherwise the filtering below would pass vacuously
    assert set(replication_path_registry.keys()) >= _EC_IDENTS | _MKP_IDENTS

    excluded = (set() if replicate_ec else _EC_IDENTS) | (set() if replicate_mkps else _MKP_IDENTS)

    assert {
        p.ident
        for p in activate_changes._get_replication_components(site_config)  # noqa: SLF001
    } == set(replication_path_registry.keys()) - excluded
