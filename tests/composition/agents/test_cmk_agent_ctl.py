#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from tests.testlib.utils import execute

from tests.composition.utils import should_skip_because_uncontainerized

# Skip all agent controller tests if we are not in a container to avoid messing up your machine
pytestmark = pytest.mark.skipif(
    should_skip_because_uncontainerized(),
    reason=("tests might mess up your local environment, eg. by installing an actual agent"),
)


def test_agent_controller_installed(agent_ctl: Path) -> None:
    res = execute([agent_ctl.as_posix(), "--help"])
    assert "Checkmk agent controller.\n\nUsage:" in res.stdout


def test_dump(agent_ctl: Path) -> None:
    res = execute(["sudo", agent_ctl.as_posix(), "dump"])
    assert res.stdout.startswith("<<<check_mk>>>")
