#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.version import Edition
from cmk.gui import main_modules
from cmk.gui.watolib.simple_config_file import config_file_registry
from cmk.plugins.diagnostics.lib._classification import (
    CheckmkFileSensitivity,
    FILE_MAP_CONFIG,
    get_checkmk_file_info,
)

# Files without a classification row yet. Delete a file from this list when you add its row.
_KNOWN_UNCLASSIFIED = {
    "etc/check_mk/conf.d/wato/passwords.mk",
    "etc/check_mk/multisite.d/broker_connections.mk",
    "etc/check_mk/multisite.d/wato/configuration_bundles.mk",
    "etc/check_mk/multisite.d/wato/roles.mk",
}


def _written_config_files() -> list[str]:
    # The registry is only filled by the plug-in registration, so run it at collection time.
    main_modules.register(Edition.COMMUNITY, debug=True)
    return sorted(path for path in config_file_registry if FILE_MAP_CONFIG.keep(Path(path)))


@pytest.mark.parametrize(
    "site_rel_path",
    [
        pytest.param(
            path,
            marks=pytest.mark.xfail(strict=True, reason="No classification row yet")
            if path in _KNOWN_UNCLASSIFIED
            else (),
        )
        for path in _written_config_files()
    ],
)
def test_written_config_file_is_classified(site_rel_path: str) -> None:
    rel_path = Path(site_rel_path).relative_to(FILE_MAP_CONFIG.rel_base_folder)

    assert get_checkmk_file_info(str(rel_path)).sensitivity is not CheckmkFileSensitivity.unknown
