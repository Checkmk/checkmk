#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import base64
import pprint
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

import cmk.utils.paths
import cmk.utils.rulesets.tuple_rulesets
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import ContactgroupName

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.utils.escaping import escape_to_html

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


class HostContactGroupSpec(TypedDict):
    groups: list[ContactgroupName]
    recurse_perms: bool
    use: bool
    use_for_services: bool
    recurse_use: bool


LegacyContactGroupSpec = tuple[bool, list[ContactgroupName]]


# TODO: Find a better place later
def convert_cgroups_from_tuple(
    value: HostContactGroupSpec | LegacyContactGroupSpec,
) -> HostContactGroupSpec:
    """Convert old tuple representation to new dict representation of folder's group settings"""
    if isinstance(value, dict):
        if "use_for_services" in value:
            return value
        return {
            "groups": value["groups"],
            "recurse_perms": value["recurse_perms"],
            "use": value["use"],
            "use_for_services": False,
            "recurse_use": value["recurse_use"],
        }

    return {
        "groups": value[1],
        "recurse_perms": False,
        "use": value[0],
        "use_for_services": False,
        "recurse_use": False,
    }


# TODO: Find a better place later
def host_attribute_matches(crit: str, value: str) -> bool:
    if crit and crit[0] == "~":
        # insensitive infix regex match
        return re.search(crit[1:], value, re.IGNORECASE) is not None

    # insensitive infix search
    return crit.lower() in value.lower()


def get_value_formatter() -> Callable[[Any], str]:
    if active_config.wato_pprint_config:
        return pprint.pformat
    return repr


def format_config_value(value: Any) -> str:
    return get_value_formatter()(value)


def mk_repr(x: Any) -> bytes:
    return base64.b64encode(repr(x).encode())


def mk_eval(s: bytes | str) -> Any:
    try:
        return ast.literal_eval(base64.b64decode(s).decode())
    except Exception:
        raise MKGeneralException(_("Unable to parse provided data: %s") % escape_to_html(repr(s)))


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
        "agent_config:mrpe",
        "agent_config:agent_paths",
        "agent_config:runas",
        "agent_config:only_from",
    ]:
        return user.may("wato.rulesets") and user.may("wato.add_or_modify_executables")
    if varname == "agent_config:custom_files":
        return user.may("wato.rulesets") and user.may("wato.agent_deploy_custom_files")
    return user.may("wato.rulesets")


def format_php(data: object, lvl: int = 1) -> str:
    """Format a python object for php"""
    s = ""
    if isinstance(data, (list, tuple)):
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
    elif isinstance(data, (int, float)):
        s += str(data)
    elif data is None:
        s += "null"
    else:
        s += format_php(str(data))

    return s
