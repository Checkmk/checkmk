#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import re
import pprint
import base64
from typing import Any, Union, List

from six import ensure_binary, ensure_str

from cmk.gui.sites import SiteStatus
from cmk.utils.werks import parse_check_mk_version

from cmk.utils.type_defs import HostName
import cmk.utils.version as cmk_version
import cmk.utils.paths
import cmk.utils.rulesets.tuple_rulesets

from cmk.gui.globals import user
from cmk.gui.globals import config
from cmk.gui.background_job import BackgroundJobAlreadyRunning
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.utils.escaping import escape_html_permissive

# TODO: Clean up all call sites in the GUI and only use them in WATO config file loading code
ALL_HOSTS = cmk.utils.rulesets.tuple_rulesets.ALL_HOSTS
ALL_SERVICES = cmk.utils.rulesets.tuple_rulesets.ALL_SERVICES
NEGATE = cmk.utils.rulesets.tuple_rulesets.NEGATE


def wato_root_dir():
    return cmk.utils.paths.check_mk_config_dir + "/wato/"


def multisite_dir():
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


# TODO: Move this to CEE specific code again
def liveproxyd_config_dir():
    return cmk.utils.paths.default_config_dir + "/liveproxyd.d/wato/"


# TODO: Find a better place later
def rename_host_in_list(thelist, oldname, newname):
    did_rename = False
    for nr, element in enumerate(thelist):
        if element == oldname:
            thelist[nr] = newname
            did_rename = True
        elif element == '!' + oldname:
            thelist[nr] = '!' + newname
            did_rename = True
    return did_rename


# Convert old tuple representation to new dict representation of
# folder's group settings
# TODO: Find a better place later
def convert_cgroups_from_tuple(value):
    if isinstance(value, dict):
        if "use_for_services" in value:
            return value
        new_value = value.copy()
        new_value.update({"use_for_services": False})
        return new_value

    return {
        "groups": value[1],
        "recurse_perms": False,
        "use": value[0],
        "use_for_services": False,
        "recurse_use": False,
    }


# TODO: Find a better place later
def host_attribute_matches(crit, value):
    if crit and crit[0] == "~":
        # insensitive infix regex match
        return re.search(crit[1:], value, re.IGNORECASE) is not None

    # insensitive infix search
    return crit.lower() in value.lower()


def format_config_value(value: Any) -> str:
    return pprint.pformat(value) if config.wato_pprint_config else repr(value)


def mk_repr(x: Any) -> bytes:
    return base64.b64encode(ensure_binary(repr(x)))


def mk_eval(s: Union[bytes, str]) -> Any:
    try:
        return ast.literal_eval(ensure_str(base64.b64decode(s)))
    except Exception:
        raise MKGeneralException(
            _('Unable to parse provided data: %s') % escape_html_permissive(repr(s)))


def has_agent_bakery():
    return not cmk_version.is_raw_edition()


def try_bake_agents_for_hosts(hosts: List[HostName]) -> None:
    if has_agent_bakery():
        import cmk.gui.cee.plugins.wato.agent_bakery.misc as agent_bakery  # pylint: disable=import-error,no-name-in-module
        try:
            agent_bakery.start_bake_agents(host_names=hosts, signing_credentials=None)
        except BackgroundJobAlreadyRunning:
            pass


def site_neutral_path(path):
    if path.startswith('/omd'):
        parts = path.split('/')
        parts[3] = '[SITE_ID]'
        return '/'.join(parts)
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


def is_pre_17_remote_site(site_status: SiteStatus) -> bool:
    """Decide which snapshot format is pushed to the given site

    The sync snapshot format was changed between 1.6 and 1.7. To support migrations with a
    new central site and an old remote site, we detect that case here and create the 1.6
    snapshots for the old sites.
    """
    version = site_status.get("livestatus_version")
    if not version:
        return False

    return parse_check_mk_version(version) < parse_check_mk_version("1.7.0i1")
