#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, get_args, Literal

import cmk.utils.paths
import cmk.utils.store as store

from cmk.gui.hooks import request_memoize

GroupType = Literal["host", "service", "contact"]
GroupName = str
# Elements:
# mandatory: alias: str
# optional: inventory_paths
# optional: nagvis_maps
# optional (CME): customer
GroupSpec = Dict[str, Any]  # TODO: Improve this type
GroupSpecs = Dict[GroupName, GroupSpec]
AllGroupSpecs = Dict[GroupType, GroupSpecs]


def load_host_group_information() -> GroupSpecs:
    return load_group_information()["host"]


def load_service_group_information() -> GroupSpecs:
    return load_group_information()["service"]


def load_contact_group_information() -> GroupSpecs:
    return load_group_information()["contact"]


@request_memoize()
def load_group_information() -> AllGroupSpecs:
    cmk_base_groups = _load_cmk_base_groups()
    gui_groups = _load_gui_groups()

    # Merge information from Checkmk and Multisite worlds together
    groups: Dict[GroupType, Dict[GroupName, GroupSpec]] = {}
    for what in get_args(GroupType):
        groups[what] = {}
        for gid, alias in cmk_base_groups["define_%sgroups" % what].items():
            groups[what][gid] = {"alias": alias}

            if gid in gui_groups["multisite_%sgroups" % what]:
                groups[what][gid].update(gui_groups["multisite_%sgroups" % what][gid])

    return groups


def _load_cmk_base_groups() -> Dict[GroupName, Dict[GroupName, str]]:
    """Load group alias maps from Checkmk world"""
    group_specs: Dict[str, Dict[GroupName, str]] = {
        "define_hostgroups": {},
        "define_servicegroups": {},
        "define_contactgroups": {},
    }

    return store.load_mk_file(
        cmk.utils.paths.check_mk_config_dir + "/wato/groups.mk", default=group_specs
    )


def _load_gui_groups() -> Dict[str, GroupSpecs]:
    # Now load information from the Web world
    group_specs: Dict[str, GroupSpecs] = {
        "multisite_hostgroups": {},
        "multisite_servicegroups": {},
        "multisite_contactgroups": {},
    }

    return store.load_mk_file(
        cmk.utils.paths.default_config_dir + "/multisite.d/wato/groups.mk", default=group_specs
    )
