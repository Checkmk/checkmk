#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from collections.abc import Generator
from pathlib import Path

import pytest

from cmk.testlib.notification_plugins import fixture_notify_context as fixture_notify_context
from cmk.utils import paths


@pytest.fixture(autouse=True, scope="session")  # ruff: ignore[pytest-fixture-autouse]
def fixture_omd_site() -> Generator[None]:
    os.environ["OMD_SITE"] = "NO_SITE"
    yield


@pytest.fixture(name="site_root")
def fixture_site_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Without OMD_ROOT all site paths are relative, so the working directory
    # acts as the site root.
    if paths.omd_root.is_absolute():
        pytest.fail(f"OMD_ROOT must not be set for these tests, got {paths.omd_root}")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _install_fake_sendmail(site_root: Path, exit_code: int) -> Path:
    # local/bin/sendmail below the site root takes precedence over the system sendmail.
    script = site_root / "local/bin/sendmail"
    script.parent.mkdir(parents=True)
    failure = f"echo boom >&2\nexit {exit_code}\n" if exit_code else ""
    script.write_text(f'#!/bin/sh\ncat > "$0.mail"\n{failure}')
    script.chmod(0o755)
    return site_root / "local/bin/sendmail.mail"


@pytest.fixture(name="fake_sendmail")
def fixture_fake_sendmail(site_root: Path) -> Path:
    """Path of the file the fake sendmail spools each mail to"""
    return _install_fake_sendmail(site_root, exit_code=0)


@pytest.fixture(name="failing_sendmail")
def fixture_failing_sendmail(site_root: Path) -> None:
    _install_fake_sendmail(site_root, exit_code=3)


@pytest.fixture(name="graph_url")
def fixture_graph_url(site_root: Path) -> re.Pattern[str]:
    (site_root / "etc/omd").mkdir(parents=True)
    (site_root / "etc/omd/site.conf").write_text("CONFIG_APACHE_TCP_PORT='5000'\n")
    return re.compile(r"http://localhost:5000/[^/]+/check_mk/ajax_graph_images\.py")
