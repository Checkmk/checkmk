#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import platform
import subprocess
import sys
import telnetlib  # nosec
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Final, Iterator, List, NamedTuple

import yaml

YamlDict = Dict[str, Dict[str, Any]]
INTEGRATION_PORT: Final = 25998
AGENT_EXE_NAME: Final = "check_mk_agent.exe"
_HOST: Final = "localhost"
USER_YAML_CONFIG: Final = "check_mk.user.yml"
SECTION_COUNT: Final = 18
ONLY_FROM_LINE: Final = 17
CTL_STATUS_LINE: Final = 19
PYTHON_CAB_NAME: Final = "python-3.cab"
CMK_UPDATER_PY: Final = "cmk_update_agent.py"
CMK_UPDATER_CHECKMK_PY: Final = "cmk_update_agent.checkmk.py"


class ExeOutput(NamedTuple):
    ret_code: int
    stdout: str
    stderr: str


def create_protocol_file(directory: Path) -> None:
    # block  upgrading
    protocol_dir = directory / "config"
    try:
        os.makedirs(protocol_dir)
    except OSError as e:
        print(f"Probably folders exist: {e}")

    if not protocol_dir.exists():
        print(f"Directory {protocol_dir} doesn't exist, may be you have not enough rights")
        sys.exit(11)

    protocol_file = protocol_dir / "upgrade.protocol"
    with open(protocol_file, "w") as f:
        f.write("Upgraded:\n   time: '2019-05-20 18:21:53.164")


def create_legacy_pull_file(directory: Path) -> None:
    # we allow legacy communication: TLS testing is not for this test
    allow_legacy_pull_file = directory / "allow-legacy-pull"
    with open(allow_legacy_pull_file, "w") as f:
        f.write("Created by integration tests")


def _get_data_using_telnet(host: str, port: int) -> List[str]:
    # overloaded CI Node may delay start/init of the agent process
    # we must retry connection few times to avoid complaints
    for _ in range(5):
        try:
            with telnetlib.Telnet(host, port, timeout=10) as telnet:  # nosec
                result = telnet.read_all().decode(encoding="cp1252")
                if result:
                    return result.splitlines()
                time.sleep(2)
        except Exception as _:
            # print('No connect, waiting for agent')
            time.sleep(2)

    return []


def get_path_from_env(env: str) -> Path:
    env_value = os.getenv(env)
    assert env_value is not None
    return Path(env_value)


def check_os() -> None:
    assert platform.system() == "Windows"


@contextmanager
def _write_config(work_config: YamlDict, data_dir: Path) -> Iterator[None]:
    yaml_file = data_dir / USER_YAML_CONFIG
    try:
        with open(yaml_file, "wt") as f:
            ret = yaml.dump(work_config)
            f.write(ret)
        yield
    finally:
        yaml_file.unlink()


def obtain_agent_data(
    work_config: YamlDict,
    *,
    main_exe: Path,
    data_dir: Path,
) -> List[str]:
    with (
        _write_config(work_config, data_dir),
        subprocess.Popen(
            [main_exe, "exec", "-integration"],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as p,
    ):
        try:
            result = _get_data_using_telnet(_HOST, INTEGRATION_PORT)
        finally:
            # NOTE. we MUST kill both processes (as a _tree_!): we do not need it.
            # Any graceful killing may require a lot of time and gives nothing to testing.
            subprocess.call(
                f'taskkill /F /T /FI "pid eq {p.pid}" /FI "IMAGENAME eq {AGENT_EXE_NAME}"'
            )

    return result


def run_agent(
    work_config: YamlDict,
    *,
    param: str,
    main_exe: Path,
    data_dir: Path,
) -> ExeOutput:
    with (
        _write_config(work_config, data_dir),
        subprocess.Popen(
            [main_exe, param],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as p,
    ):
        try:
            stdout, stderr = p.communicate(timeout=10)
            ret_code = p.returncode
        finally:
            # NOTE. we MUST kill both processes (as a _tree_!): we do not need it.
            # Any graceful killing may require a lot of time and gives nothing to testing.
            subprocess.call(
                f'taskkill /F /T /FI "pid eq {p.pid}" /FI "IMAGENAME eq {AGENT_EXE_NAME}"'
            )

    return ExeOutput(ret_code, stdout=stdout.decode(), stderr=stderr.decode())


def unpack_modules(root_dir: Path, *, module_dir: Path) -> int:
    # subprocess.call(f"expand {root_dir / PYTHON_CAB_NAME } -F:* {data_dir / 'modules'/ 'python-3'}")
    with (
        subprocess.Popen(
            [
                "expand.exe",
                f"{root_dir / PYTHON_CAB_NAME }",
                "-F:*",
                f"{module_dir}",
            ],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as p,
    ):
        _, __ = p.communicate(timeout=30)
        return p.returncode


@contextmanager
def _change_dir(to_dir: Path) -> Iterator[None]:
    p = os.getcwd()
    os.chdir(to_dir)
    yield
    os.chdir(p)


def postinstall_module(module_dir: Path) -> int:
    with (
        _change_dir(module_dir),
        subprocess.Popen(
            [
                "postinstall.cmd",
            ],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as p,
    ):
        _, __ = p.communicate(timeout=30)
        return p.returncode


def patch_venv_config(module_dir: Path) -> None:
    pyvenv_cfg = module_dir / ".venv" / "pyvenv.cfg"
    with open(pyvenv_cfg, "r+") as in_file:
        text = in_file.read()
        text = text.replace(r"C:\ProgramData\checkmk\agent\modules\python-3", f"{module_dir}")
    with open(pyvenv_cfg, "w") as out_file:
        out_file.write(text)
