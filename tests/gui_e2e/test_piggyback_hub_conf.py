#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path

from tests.testlib.site import Site

logger = logging.getLogger(__name__)


SITE_SPECIFIC_SETTINGS_REL_PATH = Path("etc/check_mk/multisite.d/sites.mk")
GLOBAL_SETTINGS_REL_PATH = Path("etc/omd/global.mk")
SITE_CONF_REL_PATH = Path("etc/omd/site.conf")


def _back_up_original_site_file_states(
    central_site: Site, remote_sites: list[Site]
) -> tuple[Sequence[Path], Mapping[Path, str]]:
    def replication_changes_rel_path(site_id: str) -> Path:
        return Path(f"var/check_mk/wato/replication_changes_{site_id}.mk")

    def replication_status_rel_path(site_id: str) -> Path:
        return Path(f"var/check_mk/wato/replication_status_{site_id}.mk")

    all_sites = [central_site] + remote_sites
    setting_files = (
        [GLOBAL_SETTINGS_REL_PATH, SITE_SPECIFIC_SETTINGS_REL_PATH, Path("etc/omd/site.conf")]
        + [replication_changes_rel_path(site.id) for site in all_sites]
        + [replication_status_rel_path(site.id) for site in all_sites]
    )
    backed_settings = {
        setting_file: central_site.read_file(setting_file)
        for setting_file in setting_files
        if central_site.file_exists(setting_file)
    }
    return setting_files, backed_settings


@contextmanager
def _setup_settings(
    global_settings: Mapping[str, object] | None,
    site_specific_settings: Mapping[str, Mapping[str, object]] | None,
    central_site: Site,
    remote_sites: list[Site],
) -> Iterator[None]:
    """Backup all relevant settings, apply global and site-specific settings that need to be set up
    as precondition to the tests, then restore original settings after the test"""
    setting_files, backed_settings = _back_up_original_site_file_states(central_site, remote_sites)

    if global_settings:
        central_site.update_global_settings(GLOBAL_SETTINGS_REL_PATH, dict(global_settings))
    if site_specific_settings:
        updated_settings = {
            site_id: {"globals": dict(settings)}
            for site_id, settings in site_specific_settings.items()
        }
        central_site.update_site_specific_settings(
            SITE_SPECIFIC_SETTINGS_REL_PATH, updated_settings
        )
    try:
        yield
    finally:
        for path in setting_files:
            if path in backed_settings:
                central_site.write_text_file(path, backed_settings[path])
            elif central_site.file_exists(path):
                central_site.delete_file(path)
