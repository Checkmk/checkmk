#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum, StrEnum, unique
from typing import Final

from cmk.bakery.v1 import OS

AGENT_FILE_HEADER: Final = (
    "# Created by Check_MK Agent Bakery.\n"
    "# This file is managed via WATO, do not edit manually or you\n"
    "# lose your changes next time when you update the agent.\n\n"
)


@unique
class LogicalPath(Enum):
    AGENT = "agent"
    BIN = "bin"
    CONFIG = "config"
    ETC = "etc"
    HOME = "home"
    LIB = "lib"
    LOCAL = "local"
    PLUGINS = "plugins"
    ROOT = "root"
    VAR = "var"


@unique
class ScriptType(StrEnum):
    PLUGIN = "plugin"
    LOCAL = "local"

    def __str__(self) -> str:
        return str(self.value)


ALL_OPSYSES: Final = (OS.LINUX, OS.SOLARIS, OS.AIX, OS.WINDOWS)


PYTHON_MODULE_EXT: Final = ".checkmk.py"
