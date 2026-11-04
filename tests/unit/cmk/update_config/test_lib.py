#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.update_config.lib import is_update_from_before_3_0

LOGGER = logging.getLogger("test")


@pytest.mark.parametrize(
    "from_version",
    [
        pytest.param("2.5.0p17.ultimate", id="patch release"),
        pytest.param("2.5.0p1-rc1.pro", id="release candidate"),
        pytest.param("2.5.0b1+security.pro", id="beta with meta data"),
        pytest.param("2.5.0-2026.10.20.ultimate", id="daily of the 2.5 branch"),
        pytest.param("2.5.0-2026.06.02-sandbox-ab-2.5-thing.pro", id="daily of a sandbox branch"),
        pytest.param("2.4.0p1.cee", id="edition of 2.4 and earlier"),
        pytest.param("2.3.0b1.cre", id="beta of 2.3"),
    ],
)
def test_update_from_before_3_0(from_version: str) -> None:
    assert is_update_from_before_3_0(from_version, LOGGER)


@pytest.mark.parametrize(
    "from_version",
    [
        pytest.param("3.0.0p1.pro", id="patch release"),
        pytest.param("3.0.0b1-rc2.pro", id="release candidate"),
        pytest.param("3.0.0-2026.11.04.pro", id="daily of the 3.0 branch"),
        pytest.param("3.1.0b1.pro", id="beta of a later version"),
        # A daily of the master branch carried no base version before 2023-11-16, so the
        # major version is unknown. Such a site is a development site, and gets no rules.
        pytest.param("2026.11.04.pro", id="daily of the master branch, old schema"),
    ],
)
def test_update_from_3_0_or_later(from_version: str) -> None:
    assert not is_update_from_before_3_0(from_version, LOGGER)


def test_new_site_is_no_update() -> None:
    assert not is_update_from_before_3_0(None, LOGGER)


def test_warns_on_unparseable_version(caplog: pytest.LogCaptureFixture) -> None:
    assert not is_update_from_before_3_0("garbage.ultimate", LOGGER)
    assert 'Cannot parse OMD_FROM_VERSION "garbage.ultimate"' in caplog.text
