#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import subprocess
from getpass import getuser
from pathlib import Path

import pytest

from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils import execute

logger = logging.getLogger(__name__)


def _write_script(script_dir: Path) -> None:
    script_dir.mkdir(exist_ok=True)
    script_file = script_dir / "whoami.sh"
    if script_file.exists():
        return
    script_file.write_text('#!/usr/bin/env bash\necho "WHOAMI: $(whoami)"', encoding="UTF-8")
    script_file.chmod(0o4744)  # necessary to be executable by anyone


def _write_config(runas_user: str, mk_confdir: Path, script_dir: Path) -> None:
    mk_confdir.mkdir(exist_ok=True)
    cfg_file = mk_confdir / "runas.cfg"
    cfg_file.write_text(f"local {runas_user} {script_dir.as_posix()}", encoding="UTF-8")


@pytest.mark.parametrize("runas_user", ["root", "user"])
def test_cmk_agent_run_runas_executor(runas_user: str, tmp_path: Path) -> None:
    # the actual username
    runas_user_name = getuser() if runas_user == "user" else runas_user
    # the argument for the runas.cfg
    runas_user_arg = "-" if runas_user_name == "root" else runas_user_name

    script_dir = tmp_path / "scripts"
    mk_confdir = tmp_path / "config"
    _write_script(script_dir=script_dir)
    _write_config(runas_user=runas_user_arg, mk_confdir=mk_confdir, script_dir=script_dir)

    agent_path = repo_path() / "agents" / "check_mk_agent.linux"

    # run the agent script as root
    agent = execute(
        ["bash", "-c", agent_path.as_posix()],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={"MK_CONFDIR": mk_confdir.as_posix()},
        preserve_env=["MK_CONFDIR"],
        sudo=True,
    )
    agent_output, _ = agent.communicate()

    # assert that the agent was run successfully
    assert agent.returncode == 0, f"The agent execution has failed! Output: {agent_output}"
    # assert that the script was run exactly once
    assert agent_output.count("WHOAMI:") == 1, "The local script was not executed exactly once!"
    # assert that the script was run as the correct user
    assert (
        f"WHOAMI: {runas_user_name}" in agent_output
    ), "The local script was not executed in the correct user context!"
