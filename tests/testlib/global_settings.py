#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from tests.testlib.site import Site

_GLOBAL_SETTINGS_FILE = "etc/check_mk/multisite.d/wato/global.mk"


def read_global_settings(site: Site) -> dict[str, object]:
    global_settings: dict[str, object] = {}
    exec(site.read_file(_GLOBAL_SETTINGS_FILE), {}, global_settings)
    return global_settings


def write_global_settings(site: Site, global_settings: Mapping[str, object]) -> None:
    site.write_text_file(
        _GLOBAL_SETTINGS_FILE,
        "\n".join(f"{key} = {repr(val)}" for key, val in global_settings.items()),
    )


def update_global_settings(site: Site, update: dict[str, object]) -> None:
    write_global_settings(site, read_global_settings(site) | update)
