#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import platform
import sys
import telnetlib  # nosec
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, TypeVar

T = TypeVar("T")
YieldFixture = Generator[T, None, None]

YamlDict = Dict[str, Dict[str, Any]]


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
    # allow legacy communication
    allow_legacy_pull_file = directory / "allow-legacy-pull"
    with open(allow_legacy_pull_file, "w") as f:
        f.write("Created by integration tests")


def get_data_from_agent(host: str, port: int) -> List[str]:
    # overloaded node may delay start of agent process
    # we have to retry connection
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
