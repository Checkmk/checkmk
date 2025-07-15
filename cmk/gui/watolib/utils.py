#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import base64
from pathlib import Path
from typing import Any

from cmk.ccc.exceptions import MKGeneralException

import cmk.utils.paths
import cmk.utils.rulesets.tuple_rulesets

from cmk.gui.i18n import _

# TODO: Clean up all call sites in the GUI and only use them in Setup config file loading code
ALL_HOSTS = cmk.utils.rulesets.tuple_rulesets.ALL_HOSTS
ALL_SERVICES = cmk.utils.rulesets.tuple_rulesets.ALL_SERVICES
NEGATE = cmk.utils.rulesets.tuple_rulesets.NEGATE


def wato_root_dir() -> Path:
    return cmk.utils.paths.check_mk_config_dir / "wato"


def multisite_dir() -> Path:
    return cmk.utils.paths.default_config_dir / "multisite.d/wato"


def mk_repr(x: Any) -> bytes:
    return base64.b64encode(repr(x).encode())


def mk_eval(s: bytes | str) -> Any:
    try:
        return ast.literal_eval(base64.b64decode(s).decode())
    except Exception:
        raise MKGeneralException(_("Unable to parse provided data: %s") % repr(s))


def site_neutral_path(path: str | Path) -> str:
    path = str(path)
    if path.startswith("/omd"):
        parts = path.split("/")
        parts[3] = "[SITE_ID]"
        return "/".join(parts)
    return path
