#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from collections.abc import Callable

import pytest

from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.update_global_proxies import (
    PreviousProxySpec,
    UpdateGlobalProxies,
)
from cmk.utils.http_proxy_config import HTTPProxySpec, ProxyAuthSpec, ProxyConfigSpec


@pytest.fixture
def _create_old_global_proxies() -> None:
    settings = ConfigDomainCore().load()
    # Since settings is a Mapping (likely an immutable dict), create a mutable copy
    settings = dict(settings)
    settings["http_proxies"] = {
        "proxy_1": PreviousProxySpec(
            title="Proxy 1",
            ident="proxy_1",
            proxy_url="http://proxy1.server:1324",
        ),
        "proxy_2": PreviousProxySpec(
            title="Proxy 2",
            ident="proxy_2",
            proxy_url="http://test_user:test_pass@proxy2.server:4132",
        ),
    }
    ConfigDomainCore().save(settings)


def test_migrate_global_proxies(_create_old_global_proxies: Callable[[], None]) -> None:
    UpdateGlobalProxies(
        name="test_migrate_global_proxies",
        title="Test Migrate Global Proxies",
        sort_index=10,
        expiry_version=ExpiryVersion.NEVER,
    )(logger=logging.getLogger("test_migrate_global_proxies"))

    settings = ConfigDomainCore().load()
    assert settings["http_proxies"] == {
        "proxy_1": HTTPProxySpec(
            title="Proxy 1",
            ident="proxy_1",
            proxy_config=ProxyConfigSpec(
                scheme="http",
                proxy_server_name="proxy1.server",
                port=1324,
                auth=None,
            ),
        ),
        "proxy_2": HTTPProxySpec(
            title="Proxy 2",
            ident="proxy_2",
            proxy_config=ProxyConfigSpec(
                scheme="http",
                proxy_server_name="proxy2.server",
                port=4132,
                auth=ProxyAuthSpec(
                    user="test_user",
                    password=("password", "test_pass"),
                ),
            ),
        ),
    }
