#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import getLogger
from pathlib import Path

from cmk.update_config.plugins.actions.remove_nagios_share import remove_nagios_share

LOGGER = getLogger()


def test_remove_nagios_share(tmp_path: Path) -> None:
    # Assemble
    nagios_theme_dir = tmp_path / "local/share/nagios/htdocs/theme/"
    nagios_theme_dir.mkdir(parents=True)
    images_link = nagios_theme_dir / "images"
    stylesheets_link = nagios_theme_dir / "stylesheets"
    images_link.symlink_to("/non/existent/images")
    stylesheets_link.symlink_to("/non/existent/stylesheets")
    # Act
    remove_nagios_share(tmp_path, LOGGER)
    # Assert
    assert not images_link.exists()
    assert not stylesheets_link.exists()
    assert not (tmp_path / "local/share/nagios/").exists()
    assert (tmp_path / "local/share/").exists()
    remove_nagios_share(tmp_path, LOGGER)
    assert (tmp_path / "local/share/").exists()
