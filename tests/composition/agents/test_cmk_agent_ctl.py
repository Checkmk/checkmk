#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from tests.testlib.pytest_helpers.marks import skip_if_not_containerized
from tests.testlib.utils import execute


@skip_if_not_containerized
def test_agent_controller_installed(agent_ctl: Path) -> None:
    res = execute([agent_ctl.as_posix(), "--help"])
    assert "Checkmk agent controller.\n\nUsage:" in res.stdout


@skip_if_not_containerized
def test_dump(agent_ctl: Path) -> None:
    res = execute(["sudo", agent_ctl.as_posix(), "dump"])
    assert res.stdout.startswith("<<<check_mk>>>")
