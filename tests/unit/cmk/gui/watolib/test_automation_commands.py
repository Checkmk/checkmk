#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils import paths

from cmk.gui.watolib.automation_commands import AutomationPing


def _write_site_conf(content: str) -> None:
    site_conf = paths.omd_root / "etc" / "omd" / "site.conf"
    site_conf.parent.mkdir(parents=True, exist_ok=True)
    site_conf.write_text(content)


def test_ping_reports_message_broker_as_disabled_without_piggyback_hub() -> None:
    _write_site_conf("CONFIG_PIGGYBACK_HUB='off'\n")

    response = AutomationPing().execute(None)

    assert response["omd_status"] == {"rabbitmq": 5}


def test_ping_reports_message_broker_as_enabled_with_piggyback_hub() -> None:
    _write_site_conf("CONFIG_PIGGYBACK_HUB='on'\n")

    response = AutomationPing().execute(None)

    assert response["omd_status"] == {"rabbitmq": 0}
