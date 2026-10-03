#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from logging import getLogger

import pytest

from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.warn_encoded_proxy_credentials import (
    proxies_with_encoded_credentials,
    WarnEncodedProxyCredentials,
)


def _proxy(title: str, user: str, password: object) -> dict[str, object]:
    return {
        "ident": title,
        "title": title,
        "proxy_config": {
            "scheme": "http",
            "proxy_server_name": "proxy.lan",
            "port": 3128,
            "auth": {"user": user, "password": password},
        },
    }


def _explicit(secret: str) -> tuple[str, str, tuple[str, str]]:
    return ("cmk_postprocessed", "explicit_password", ("uuid1", secret))


@pytest.mark.parametrize(
    "proxy, flagged",
    [
        pytest.param(_proxy("p", "user", _explicit("p%40ss")), True, id="encoded password"),
        pytest.param(_proxy("p", "us%3Aer", _explicit("s3crit")), True, id="encoded user"),
        pytest.param(
            _proxy("p", "user", ("cmk_postprocessed", "stored_password", ("pw", ""))),
            True,
            id="encoded stored password",
        ),
        pytest.param(_proxy("p", "user", _explicit("100%")), False, id="plain percent sign"),
        pytest.param(_proxy("p", "user", _explicit("s3crit")), False, id="plain credentials"),
        pytest.param(
            {"ident": "p", "title": "p", "proxy_config": {"scheme": "http"}},
            False,
            id="no authentication",
        ),
    ],
)
def test_proxies_with_encoded_credentials(proxy: dict[str, object], flagged: bool) -> None:
    assert proxies_with_encoded_credentials({"p": proxy}, {"pw": "p%40ss"}) == (
        ["p"] if flagged else []
    )


@pytest.mark.usefixtures("request_context")
def test_the_warning_names_the_proxy_but_not_its_credentials(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ConfigDomainCore().save(
        {"http_proxies": {"corp": _proxy("Corp proxy", "user", _explicit("p%40ss"))}}
    )

    with caplog.at_level(logging.WARNING):
        WarnEncodedProxyCredentials(
            name="warn_encoded_proxy_credentials",
            title="",
            sort_index=100,
            expiry_version=ExpiryVersion.CMK_310,
        )(getLogger())

    assert "Corp proxy" in caplog.text
    assert "p%40ss" not in caplog.text
