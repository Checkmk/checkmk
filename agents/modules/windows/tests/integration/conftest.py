#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
import tempfile
from pathlib import Path
from subprocess import PIPE, Popen
from typing import List, Optional

import pytest  # type: ignore[import]


def pytest_addoption(parser):
    parser.addoption("--expected_version", action="store", default="3.10.4")


tested_pythons = ["python-3.4.cab", "python-3.cab"]
# I know this is not a best method to reach artifacts, but in Windows not so many options.
artifact_location = Path("..\\..\\..\\..\\..\\artefacts")


@pytest.fixture(scope="session", name="expected_version")
def fixture_expected_version(pytestconfig):
    return pytestconfig.getoption("expected_version")


# NOTE: unpacked python can work only in predefined folder(pyvenv.cfg  points on it).
# We must do two things.
# 1. Check that content of pyvenv.cfg is suitable to be used in agent(points on ProgramData).
# 2. Change pyvenv.cfg so that we could test our scripts: replace ProgramData with temp
# Above mentioned things must be done in fixture, while decompression process is quite expensive.
# Also this give possibility to test literally everything
@pytest.fixture(scope="session", name="regression_data")
def fixture_regression_data(expected_version):
    return {
        "python-3.cab": b"".join(
            [
                b"home = C:\\ProgramData\\checkmk\\agent\\modules\\python-3\r\n",
                b"version_info = ",
                expected_version.encode(),
                b"\r\n",
                b"include-system-site-packages = false\r\n",
            ]
        ),
        "python-3.4.cab": b"home = C:\\ProgramData\\checkmk\\agent\\modules\\python-3\r\n"
        b"version_info = 3.4.4\r\n"
        b"include-system-site-packages = false\r\n",
    }


client_module_root = b"C:\\ProgramData\\checkmk\\agent\\modules\\python-3"


@pytest.fixture(scope="session", autouse=True, name="python_subdir")
def fixture_python_subdir():
    tmpdir = tempfile.mkdtemp()
    subdir = os.path.join(tmpdir, "modules")
    os.makedirs(subdir)
    yield Path(subdir)
    shutil.rmtree(tmpdir)


def run_proc(command: List[str], *, cwd: Optional[Path] = None):
    with Popen(command, stdout=PIPE, stderr=PIPE, cwd=cwd) as process:
        pipe, err = process.communicate()
        ret = process.wait()
    assert ret == 0, (
        f"Code {ret}\n"
        + f"Pipe:\n{pipe.decode('utf-8') if pipe else ''}\n"
        + f"Err\n{err.decode('utf-8') if err else ''}"
    )


@pytest.fixture(scope="session", autouse=True)
def python_to_test(python_subdir, regression_data) -> Path:
    """This is quite complicated simulator to verify python module and prepare the module for
    testing. During deployment every step will be validated, not because it is required(this method
    also contradicts a bit to the TDD philosophy), but to prevent extremely strange errors during
    testing phase.
    Tasks:
    1. Unpacks a python.
    2. Validates pyvenv.cfg to be suitable.
    3. Patch pyvenv.h for testing environment
    4. Calls postinstall.cmd
    5. Validates result.
    """

    for python in [Path(x) for x in tested_pythons]:
        python_file = artifact_location / python
        assert python_file.exists()

        # prepare target dir as client
        work_dir = python_subdir / python.name
        os.mkdir(work_dir)

        # deploy python precisely as done by a client
        run_proc(["expand.exe", f"{python_file}", "-F:*", f"{work_dir}"])
        venv_cfg = work_dir / ".venv" / "pyvenv.cfg"

        # check that pyvenv.cfg is good for deployment.
        with open(venv_cfg, "rb") as f:
            assert f.read() == regression_data[str(python)]

        # patch pyvenv.cfg to be valid for testing environment:
        # tests do not use well known path in ProgramData/checkmk/agent
        with open(venv_cfg, "wb") as f:
            f.write(regression_data[str(python)].replace(client_module_root, bytes(work_dir)))

        # apply postinstall step to prepare the python
        run_proc([work_dir / "postinstall.cmd"], cwd=work_dir)
        assert (work_dir / "DLLs").exists()

    return python_subdir
