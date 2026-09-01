#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

import pytest

from cmk.plugins.diagnostics.lib._classification import (
    CheckmkFileSensitivity,
    FILE_MAP_LOG,
    get_checkmk_file_info,
    OPT_COMP_BUSINESS_INTELLIGENCE,
    OPT_COMP_GLOBAL_SETTINGS,
    OPT_COMP_HOSTS_AND_FOLDERS,
    OPT_COMP_NOTIFICATIONS,
)


# 'sensitivity.value == CheckmkFileSensitivity.unknown' means not found
@pytest.mark.parametrize(
    "component, sensitivity_values",
    [
        (
            OPT_COMP_GLOBAL_SETTINGS,
            [
                CheckmkFileSensitivity.insensitive,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
            ],
        ),
        (
            OPT_COMP_HOSTS_AND_FOLDERS,
            [
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.insensitive,
            ],
        ),
        (
            OPT_COMP_NOTIFICATIONS,
            [
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.insensitive,
            ],
        ),
        (
            OPT_COMP_BUSINESS_INTELLIGENCE,
            [
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.sensitive,
            ],
        ),
    ],
)
def test_diagnostics_get_checkmk_file_info_by_name(
    component: str, sensitivity_values: Sequence[CheckmkFileSensitivity]
) -> None:
    rel_filepaths = [
        "path/to/sites.mk",
        "path/to/global.mk",
        "path/to/hosts.mk",
        "path/to/rules.mk",
        "path/to/tags.mk",
        "path/to/.wato",
        "multisite.d/wato/bi_config.bi",
    ]
    for rel_filepath, result in zip(rel_filepaths, sensitivity_values):
        assert get_checkmk_file_info(rel_filepath, component).sensitivity.value == result.value


@pytest.mark.parametrize(
    "rel_filepath, sensitivity",
    [
        ("apache.conf", CheckmkFileSensitivity.insensitive),
        ("apache.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("conf.d/microcore.mk", CheckmkFileSensitivity.insensitive),
        ("conf.d/mkeventd.mk", CheckmkFileSensitivity.insensitive),
        ("conf.d/pnp4nagios.mk", CheckmkFileSensitivity.insensitive),
        ("conf.d/wato/.wato", CheckmkFileSensitivity.insensitive),
        (
            "conf.d/wato/alert_handlers.mk",
            CheckmkFileSensitivity.high_sensitive,
        ),
        ("conf.d/wato/contacts.mk", CheckmkFileSensitivity.sensitive),
        ("conf.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("conf.d/wato/groups.mk", CheckmkFileSensitivity.insensitive),
        ("conf.d/wato/hosts.mk", CheckmkFileSensitivity.sensitive),
        (
            "conf.d/wato/notifications.mk",
            CheckmkFileSensitivity.sensitive,
        ),
        ("conf.d/wato/rules.mk", CheckmkFileSensitivity.sensitive),
        ("conf.d/wato/tags.mk", CheckmkFileSensitivity.sensitive),
        ("dcd.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("liveproxyd.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("main.mk", CheckmkFileSensitivity.insensitive),
        ("mkeventd.d/wato/rules.mk", CheckmkFileSensitivity.sensitive),
        (
            "mkeventd.d/wato/global.mk",
            CheckmkFileSensitivity.sensitive,
        ),
        ("mkeventd.mk", CheckmkFileSensitivity.insensitive),
        ("mknotifyd.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("multisite.d/liveproxyd.mk", CheckmkFileSensitivity.insensitive),
        ("multisite.d/mkeventd.mk", CheckmkFileSensitivity.insensitive),
        ("multisite.d/sites.mk", CheckmkFileSensitivity.sensitive),
        (
            "multisite.d/wato/global.mk",
            CheckmkFileSensitivity.sensitive,
        ),
        ("multisite.d/wato/groups.mk", CheckmkFileSensitivity.insensitive),
        ("multisite.d/wato/tags.mk", CheckmkFileSensitivity.sensitive),
        (
            "multisite.d/wato/users.mk",
            CheckmkFileSensitivity.sensitive,
        ),
        ("multisite.mk", CheckmkFileSensitivity.insensitive),
        ("rrdcached.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("alerts.log", CheckmkFileSensitivity.sensitive),
        ("apache/access_log", CheckmkFileSensitivity.high_sensitive),
        ("apache/error_log", CheckmkFileSensitivity.sensitive),
        ("apache/stats", CheckmkFileSensitivity.high_sensitive),
        ("cmc.log", CheckmkFileSensitivity.sensitive),
        ("unknown.log", CheckmkFileSensitivity.unknown),
        ("dcd.log", CheckmkFileSensitivity.sensitive),
        ("diskspace.log", CheckmkFileSensitivity.insensitive),
        ("liveproxyd.log", CheckmkFileSensitivity.sensitive),
        ("liveproxyd.state", CheckmkFileSensitivity.sensitive),
        ("mkeventd.log", CheckmkFileSensitivity.sensitive),
        ("mknotifyd.log", CheckmkFileSensitivity.sensitive),
        ("mknotifyd.state", CheckmkFileSensitivity.sensitive),
        ("notify.log", CheckmkFileSensitivity.sensitive),
        ("rrdcached.log", CheckmkFileSensitivity.sensitive),
        ("web.log", CheckmkFileSensitivity.sensitive),
    ],
)
def test_diagnostics_file_info_of_comp_notifications(
    rel_filepath: str, sensitivity: CheckmkFileSensitivity
) -> None:
    assert get_checkmk_file_info(rel_filepath, None).sensitivity.value == sensitivity.value


@pytest.mark.parametrize(
    "file_name, keep",
    [
        ("network-flow.log", True),
        ("network-flow.log.1", True),
        ("network-flow.log.2.gz", True),
        ("apache/access_log.1", True),
        ("mknotifyd.state", True),
        ("update.log.2.gz", True),
        ("network-flow.pid", False),
    ],
)
def test_diagnostics_log_file_map_keeps_rotations(file_name: str, keep: bool) -> None:
    assert FILE_MAP_LOG.keep(Path(file_name)) is keep
