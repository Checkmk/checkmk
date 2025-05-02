#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
import platform
import re
import subprocess
import sys
from pathlib import Path

import yaml

from . import it_utils

DEFAULT_CONFIG = """
global:
  enabled: true
  logging:
    debug: true
  port: {}
"""

if not it_utils.check_os():
    print(f"Unsupported platform {platform.system()}")
    sys.exit(13)


def get_main_yaml_name(base_dir):
    return os.path.join(base_dir, "check_mk.yml")


def get_user_yaml_name(base_dir):
    return os.path.join(
        base_dir,
    )


def get_main_plugins_name(base_dir):
    return os.path.join(base_dir, "plugins")


def create_protocol_file(on_dir):
    # block  upgrading
    protocol_dir = on_dir / "config"
    try:
        os.makedirs(protocol_dir)
    except OSError as e:
        print(f"Probably folders exist: {e}")

    if not protocol_dir.exists():
        print(f"Directory {protocol_dir} doesnt exist, may be you have not enough rights")
        sys.exit(11)

    protocol_file = protocol_dir / "upgrade.protocol"
    with open(protocol_file, "w") as f:
        f.write("Upgraded:\n   time: '2019-05-20 18:21:53.164")


def _get_path_from_env(env: str) -> Path:
    env_value = os.getenv(env)
    assert env_value is not None
    return Path(env_value)


port = 29998
host = "localhost"
EXE_ENV_VAR = "WNX_REGRESSION_BASE_DIR"
REPO_ROOT_ENV_VAR = "repo_root"
ARTIFACTS_DIR = "artefacts"

repo_root = _get_path_from_env(REPO_ROOT_ENV_VAR)
test_dir = _get_path_from_env(EXE_ENV_VAR)
if not (repo_root / ARTIFACTS_DIR).exists():
    print(f"Artifacts Directory {repo_root / ARTIFACTS_DIR} doesn't exist")
    sys.exit(11)

if not test_dir.exists():
    print(f"Test Directory {test_dir} doesnt exist")
    sys.exit(1)

# root dir
root_dir = test_dir / "test" / "root"
user_dir = test_dir / "test" / "data"

create_protocol_file(on_dir=user_dir)

# names
user_yaml_config = user_dir / "check_mk.user.yml"
main_exe = root_dir / "check_mk_agent.exe"

if not main_exe.exists():
    print(f"exe file {main_exe} doesn't exist")
    sys.exit(1)


# environment variable set
def run_subprocess(cmd):
    sys.stderr.write(" ".join(str(cmd)) + "\n")
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        stdout, stderr = p.communicate(timeout=10)
        return p.returncode, stdout, stderr


def run_agent(cmd):
    return subprocess.Popen([cmd, "exec"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def assert_subprocess(cmd):
    exit_code, stdout_ret, stderr_ret = run_subprocess(cmd)

    if stdout_ret:
        sys.stdout.write(stdout_ret.decode(encoding="cp1252"))

    if stderr_ret:
        sys.stderr.write(stderr_ret.decode(encoding="cp1252"))

    assert exit_code == 0, "'%s' failed" % " ".join(cmd)


class DuplicateSectionError(Exception):
    """Raised when a section is multiply-created."""

    def __init__(self, section) -> None:  # type: ignore[no-untyped-def]
        super().__init__(self, "Section %r already exists" % section)


class NoSectionError(Exception):
    """Raised when no section matches a requested option."""

    def __init__(self, section) -> None:  # type: ignore[no-untyped-def]
        super().__init__(self, "No section: %r" % section)


class YamlWriter:
    def __init__(self) -> None:
        self._doc = None

    def load_document(self, doc):
        self._doc = yaml.safe_load(doc)


def local_test(
    expected_output_from_agent,
    actual_output_from_agent,
    current_test,
    test_name=None,
    test_class=None,
):
    comparison_data = list(zip(expected_output_from_agent, actual_output_from_agent))
    for expected, actual in comparison_data:
        # Uncomment for debug prints:
        # if re.match(expected, actual) is None:
        #    print("ups: %s" % actual)
        #    print( 'DEBUG: actual output\r\n', '\r\n'.join(actual))
        #    print('DEBUG: expected output\r\n', '\r\n'.join(expected))
        # print("EXPECTED: %r\n ACTUAL  : %r\n" % (expected, actual))

        assert expected == actual or re.match(expected, actual) is not None, (
            f"\nExpected '{expected!r}'\nActual   '{actual!r}'"
        )
    try:
        assert len(actual_output_from_agent) >= len(expected_output_from_agent), (
            "actual output is shorter than expected:\n"
            "expected output:\n%s\nactual output:\n%s"
            % ("\n".join(expected_output_from_agent), "\n".join(actual_output_from_agent))
        )
        assert len(actual_output_from_agent) <= len(expected_output_from_agent), (
            "actual output is longer than expected:\n"
            "expected output:\n%s\nactual output:\n%s"
            % ("\n".join(expected_output_from_agent), "\n".join(actual_output_from_agent))
        )
    except TypeError:
        # expected_output may be an iterator without len
        assert len(actual_output_from_agent) > 0, "Actual output was empty"
