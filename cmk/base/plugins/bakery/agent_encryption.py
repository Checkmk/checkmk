#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from pathlib import Path
from shlex import quote

from .bakery_api.v1 import (
    FileGenerator,
    OS,
    PluginConfig,
    register,
    WindowsConfigGenerator,
    WindowsGlobalConfigEntry,
)


def get_agent_encryption_files(conf: Mapping[str, str | None]) -> FileGenerator:
    if not (passphrase := conf["passphrase"]):
        return
    yield PluginConfig(
        base_os=OS.LINUX,
        lines=list(get_agent_encryption_lines(passphrase)),
        target=Path("encryption.cfg"),
        include_header=True,
    )
    yield PluginConfig(
        base_os=OS.SOLARIS,
        lines=list(get_agent_encryption_lines(passphrase)),
        target=Path("encryption.cfg"),
        include_header=True,
    )


def get_agent_encryption_lines(passphrase: str) -> Iterable[str]:
    yield "PASSPHRASE=%s" % quote(passphrase)
    yield "ENCRYPTED=yes"


def get_agent_encryption_windows_config(conf: Mapping[str, str | None]) -> WindowsConfigGenerator:
    if not (passphrase := conf["passphrase"]):
        return
    yield WindowsGlobalConfigEntry(name="passphrase", content=passphrase)
    yield WindowsGlobalConfigEntry(name="encrypted", content="yes")


register.bakery_plugin(
    name="agent_encryption",
    files_function=get_agent_encryption_files,
    windows_config_function=get_agent_encryption_windows_config,
)
