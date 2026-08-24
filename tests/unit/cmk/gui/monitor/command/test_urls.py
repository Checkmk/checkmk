#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.monitor.command import (
    acknowledge_presets_url,
    downtime_presets_url,
    notification_rules_url,
)


def _without_setup(config: Config) -> Config:
    """The same config with Setup switched off.

    `dataclasses.replace` runs `__post_init__` again, which drops the raw mapping,
    so put it back - a gate reading `config.raw` would otherwise see nothing.
    """
    disabled = dataclasses.replace(config, wato_enabled=False)
    disabled._raw_config = config.raw
    return disabled


def test_all_links_offered_to_admin(with_admin_login: UserId, load_config: Config) -> None:
    assert (
        acknowledge_presets_url(load_config)
        == "wato.py?mode=edit_configvar&varname=acknowledge_problems"
    )
    assert notification_rules_url(load_config) == "wato.py?mode=notifications"
    assert (
        downtime_presets_url(load_config)
        == "wato.py?mode=edit_configvar&varname=user_downtime_timeranges"
    )


def test_no_links_without_the_setup_permissions(
    with_user_login: UserId, load_config: Config
) -> None:
    """Offering a link into a mode the user may not open would only produce an error page."""
    assert acknowledge_presets_url(load_config) is None
    assert notification_rules_url(load_config) is None
    assert downtime_presets_url(load_config) is None


def test_no_links_without_setup(with_admin_login: UserId, load_config: Config) -> None:
    """wato.py serves no mode at all where Setup is disabled."""
    config = _without_setup(load_config)

    assert acknowledge_presets_url(config) is None
    assert notification_rules_url(config) is None
    assert downtime_presets_url(config) is None
