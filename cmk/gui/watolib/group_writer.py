#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import get_args

import cmk.utils.paths
import cmk.utils.store as store

from cmk.gui.groups import (
    AllGroupSpecs,
    clear_group_information_request_cache,
    GroupName,
    GroupSpec,
    GroupType,
)
from cmk.gui.watolib.config_domain_name import wato_fileheader
from cmk.gui.watolib.utils import format_config_value


def save_group_information(
    all_groups: AllGroupSpecs,
    custom_default_config_dir: str | None = None,
) -> None:
    if custom_default_config_dir:
        check_mk_config_dir = "%s/conf.d/wato" % custom_default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % custom_default_config_dir
    else:
        check_mk_config_dir = "%s/conf.d/wato" % cmk.utils.paths.default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % cmk.utils.paths.default_config_dir

    _save_cmk_base_groups(all_groups, check_mk_config_dir)
    _save_gui_groups(all_groups, multisite_config_dir)

    clear_group_information_request_cache()


def _save_cmk_base_groups(all_groups: AllGroupSpecs, config_dir: str) -> None:
    check_mk_groups: dict[GroupType, dict[GroupName, str]] = {}
    for group_type, groups in all_groups.items():
        check_mk_groups[group_type] = {}
        for gid, group in groups.items():
            check_mk_groups[group_type][gid] = group["alias"]

    # Save Checkmk world related parts
    store.makedirs(config_dir)
    output = wato_fileheader()
    for group_type in get_args(GroupType):
        if check_mk_groups.get(group_type):
            output += f"if type(define_{group_type}groups) != dict:\n    define_{group_type}groups = {{}}\n"
            output += "define_{}groups.update({})\n\n".format(
                group_type,
                format_config_value(check_mk_groups[group_type]),
            )
    store.save_text_to_file("%s/groups.mk" % config_dir, output)


def _save_gui_groups(all_groups: AllGroupSpecs, config_dir: str) -> None:
    multisite_groups: dict[GroupType, dict[GroupName, GroupSpec]] = {}

    for group_type, groups in all_groups.items():
        for gid, group in groups.items():
            for attr, value in group.items():
                if attr != "alias":  # Saved in cmk_base
                    multisite_groups.setdefault(group_type, {})
                    multisite_groups[group_type].setdefault(gid, {})
                    multisite_groups[group_type][gid][attr] = value

    store.makedirs(config_dir)
    output = wato_fileheader()
    for what in get_args(GroupType):
        if multisite_groups.get(what):
            output += "multisite_{}groups = \\\n{}\n\n".format(
                what,
                format_config_value(multisite_groups[what]),
            )
    store.save_text_to_file("%s/groups.mk" % config_dir, output)
