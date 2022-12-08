#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from pytest import MonkeyPatch
from saml2.config import SPConfig

from cmk.gui.userdb.saml2.connector import Connector


def test_connector(monkeypatch: MonkeyPatch, config: SPConfig, raw_config: dict[str, Any]) -> None:
    monkeypatch.setattr(
        "cmk.gui.userdb.saml2.interface.raw_config_to_saml_config", lambda c: config
    )
    connector = Connector(raw_config)
    assert connector.is_enabled()
