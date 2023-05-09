#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from pathlib import Path
import os

from subprocess import (Popen, PIPE)
from typing import Tuple


def run_script(work_python: Path, *, script: Path) -> Tuple[int, str, str]:
    """Returns exit code, stdout and stderr"""

    exe = work_python / ".venv" / "Scripts" / "python.exe"
    # In fact we do not need asserting here, but in integration test is difficult to find
    # source of error want to know/
    assert exe.exists()
    assert script.exists()

    process = Popen([exe, script], stdout=PIPE, stderr=PIPE)
    pipe, err = process.communicate()
    ret = process.wait()

    return ret, pipe.decode("utf-8"), err.decode("utf-8")


@pytest.mark.parametrize("script,expected_code,expected_pipe,expected_err", [
    (
        Path("..\\..\\..\\..\\..\\enterprise\\agents\\plugins\\cmk_update_agent.py"),
        1,
        "",
        "Missing config file at .\\cmk-update-agent.cfg. Configuration",
    ),
    (
        Path("..\\..\\..\\..\\plugins\\mk_logwatch.py"),
        0,
        "<<<logwatch>>>",
        "",
    ),
    (
        Path("..\\..\\..\\..\\plugins\\mk_jolokia.py"),
        0,
        "<<<jolokia_info:sep(0)>>>",
        "",
    ),
])
def test_other_scripts(python_to_test: Path, script: Path, expected_code: int, expected_pipe: str,
                       expected_err: str):
    pythons = python_to_test
    for python_name in os.listdir(pythons):
        # Call the script using deployed python as client does
        ret, pipe, err = run_script(Path(python_to_test / python_name), script=script)

        # Check results as client does
        assert ret == expected_code
        assert pipe.find(expected_pipe) != -1
        assert err.find(expected_err) != -1
