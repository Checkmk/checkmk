#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from tests.testlib.utils import run

logger = logging.getLogger(__name__)


@pytest.mark.skip_if_not_containerized
def test_agent_controller_installed(agent_ctl: Path) -> None:
    res = run([agent_ctl.as_posix(), "--help"])
    assert "Checkmk agent controller.\n\nUsage:" in res.stdout


@pytest.mark.skip_if_not_containerized
def test_dump(agent_ctl: Path) -> None:
    res = run([agent_ctl.as_posix(), "dump"], sudo=True)
    assert res.stdout.startswith("<<<check_mk>>>")
