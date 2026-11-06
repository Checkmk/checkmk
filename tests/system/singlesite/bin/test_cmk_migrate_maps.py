#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
from collections.abc import Iterator

import pytest

from tests.testlib.system.site import Site

LOGGER = logging.getLogger(__name__)

_MAP = "cmk_migrate_maps_test"
_CFG = f"etc/nagvis/maps/{_MAP}.cfg"
_USER_MAPS = "var/check_mk/web/cmkadmin/user_maps.mk"
_RECORD = "var/maps/nagvis_maps_migration.mk"


@pytest.fixture(name="restored_maps")
def fixture_restored_maps(site: Site) -> Iterator[None]:
    saved = {
        path: site.read_file(path) if site.file_exists(path) else None
        for path in (_USER_MAPS, _RECORD)
    }
    yield
    site.delete_file(_CFG)
    for path, content in saved.items():
        if content is None:
            site.delete_file(path)
        else:
            site.write_file(path, content)
    site.activate_changes_and_wait_for_core_reload()


def _write_nagvis_map(site: Site, alias: str) -> None:
    site.write_file(_CFG, f"define global {{\nalias={alias}\n}}\n")


def _migrate(site: Site, *args: str) -> None:
    p = site.run(["cmk-migrate-maps", *args])
    LOGGER.info("STDOUT: %s", p.stdout)
    LOGGER.info("STDERR: %s", p.stderr)


def _alias(site: Site) -> object:
    return ast.literal_eval(site.read_file(_USER_MAPS))[_MAP]["map_spec"]["alias"]


# Cloud does not ship NagVis, so it has no NagVis maps to migrate.
@pytest.mark.skip_if_edition("cloud")
@pytest.mark.usefixtures("restored_maps")
def test_cmk_migrate_maps_brings_nagvis_changes_over_when_forced(site: Site) -> None:
    # E2E sanity check only; the migration itself is covered by test_nagvis_maps.py.
    _write_nagvis_map(site, "First")
    _migrate(site, _MAP)
    _write_nagvis_map(site, "Second")

    _migrate(site, "-f", _MAP)

    assert _alias(site) == "Second"
