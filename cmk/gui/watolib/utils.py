#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import base64
import re
from pathlib import Path
from typing import Any

from cmk.ccc.exceptions import MKGeneralException

import cmk.utils.paths
import cmk.utils.rulesets.tuple_rulesets
from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.watolib.mode import mode_registry

# TODO: Clean up all call sites in the GUI and only use them in Setup config file loading code
ALL_HOSTS = cmk.utils.rulesets.tuple_rulesets.ALL_HOSTS
ALL_SERVICES = cmk.utils.rulesets.tuple_rulesets.ALL_SERVICES
NEGATE = cmk.utils.rulesets.tuple_rulesets.NEGATE


def wato_root_dir() -> str:
    return cmk.utils.paths.check_mk_config_dir + "/wato/"


def multisite_dir() -> str:
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


# TODO: Move this to CEE specific code again
def liveproxyd_config_dir() -> str:
    return cmk.utils.paths.default_config_dir + "/liveproxyd.d/wato/"


# TODO: Find a better place later
def rename_host_in_list(thelist: list[str], oldname: str, newname: str) -> bool:
    did_rename = False
    for nr, element in enumerate(thelist):
        if element == oldname:
            thelist[nr] = newname
            did_rename = True
        elif element == "!" + oldname:
            thelist[nr] = "!" + newname
            did_rename = True
    return did_rename


# TODO: Find a better place later
def host_attribute_matches(crit: str, value: str) -> bool:
    if crit and crit[0] == "~":
        # insensitive infix regex match
        return re.search(crit[1:], value, re.IGNORECASE) is not None

    # insensitive infix search
    return crit.lower() in value.lower()


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


def may_edit_ruleset(varname: str) -> bool:
    if varname == "ignored_services":
        return user.may("wato.services") or user.may("wato.rulesets")
    if varname in [
        "custom_checks",
        "datasource_programs",
        RuleGroup.AgentConfig("mrpe"),
        RuleGroup.AgentConfig("agent_paths"),
        RuleGroup.AgentConfig("runas"),
        RuleGroup.AgentConfig("only_from"),
        RuleGroup.AgentConfig("python_plugins"),
        RuleGroup.AgentConfig("lnx_remote_alert_handlers"),
    ]:
        return user.may("wato.rulesets") and user.may("wato.add_or_modify_executables")
    if varname == RuleGroup.AgentConfig("custom_files"):
        return user.may("wato.rulesets") and user.may("wato.agent_deploy_custom_files")
    return user.may("wato.rulesets")


def format_php(data: object, lvl: int = 1) -> str:
    """Format a python object for php"""
    s = ""
    if isinstance(data, list | tuple):
        s += "array(\n"
        for item in data:
            s += "    " * lvl + format_php(item, lvl + 1) + ",\n"
        s += "    " * (lvl - 1) + ")"
    elif isinstance(data, dict):
        s += "array(\n"
        for key, val in data.items():
            s += "    " * lvl + format_php(key, lvl + 1) + " => " + format_php(val, lvl + 1) + ",\n"
        s += "    " * (lvl - 1) + ")"
    elif isinstance(data, str):
        s += "'%s'" % re.sub(r"('|\\)", r"\\\1", data)
    elif isinstance(data, bool):
        s += data and "true" or "false"
    elif isinstance(data, int | float):
        s += str(data)
    elif data is None:
        s += "null"
    else:
        s += format_php(str(data))

    return s


def ldap_connections_are_configurable() -> bool:
    return mode_registry.get("ldap_config") is not None
