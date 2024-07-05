#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import pprint
from datetime import datetime
from typing import Literal, TypedDict

from cmk.gui import userdb
from cmk.gui.config import load_config
from cmk.gui.watolib.config_domain_name import wato_fileheader
from cmk.gui.watolib.host_attributes import transform_pre_16_host_topics
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.utils import multisite_dir

from cmk.ccc import store


class CustomAttrSpec(TypedDict):
    type: Literal["TextAscii"]
    name: str
    title: str
    topic: str
    help: str
    # None case should be cleaned up to False
    show_in_table: bool | None
    # None case should be cleaned up to False
    add_custom_macro: bool | None


class CustomHostAttrSpec(CustomAttrSpec): ...


class CustomUserAttrSpec(CustomAttrSpec):
    # None case should be cleaned up to False
    user_editable: bool | None


class CustomAttrSpecs(TypedDict):
    user: list[CustomUserAttrSpec]
    host: list[CustomHostAttrSpec]


def update_user_custom_attrs(now: datetime) -> None:
    userdb.update_config_based_user_attributes()
    userdb.rewrite_users(now)


def update_host_custom_attrs():
    load_config()
    tree = folder_tree()
    tree.invalidate_caches()
    tree.root_folder().rewrite_hosts_files()


def load_custom_attrs_from_mk_file(lock: bool) -> CustomAttrSpecs:
    filename = os.path.join(multisite_dir(), "custom_attrs.mk")
    vars_ = store.load_mk_file(
        filename,
        {
            "wato_user_attrs": [],
            "wato_host_attrs": [],
        },
        lock=lock,
    )

    return CustomAttrSpecs(
        {
            # Next step: Parse data to get rid of the annotations
            "user": vars_.get("wato_user_attrs", []),  # type: ignore[typeddict-item]
            "host": transform_pre_16_host_topics(vars_.get("wato_host_attrs", [])),  # type: ignore[arg-type,typeddict-item]
        }
    )


def save_custom_attrs_to_mk_file(attrs: CustomAttrSpecs) -> None:
    output = wato_fileheader()

    if attrs["user"]:
        output += "if type(wato_user_attrs) != list:\n    wato_user_attrs = []\n"
        output += f"wato_user_attrs += {pprint.pformat(attrs['user'])}\n\n"

    if attrs["host"]:
        output += "if type(wato_host_attrs) != list:\n    wato_host_attrs = []\n"
        output += f"wato_host_attrs += {pprint.pformat(attrs['host'])}\n\n"

    store.mkdir(multisite_dir())
    store.save_text_to_file(multisite_dir() + "custom_attrs.mk", output)
