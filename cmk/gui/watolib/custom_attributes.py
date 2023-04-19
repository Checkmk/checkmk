#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import pprint
from datetime import datetime

from cmk.utils import store

from cmk.gui import userdb
from cmk.gui.config import load_config
from cmk.gui.plugins.watolib.utils import wato_fileheader
from cmk.gui.watolib.host_attributes import transform_pre_16_host_topics
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.utils import multisite_dir


def update_user_custom_attrs(now: datetime):  # type: ignore[no-untyped-def]
    userdb.update_config_based_user_attributes()
    userdb.rewrite_users(now)


def update_host_custom_attrs():
    load_config()
    Folder.invalidate_caches()
    Folder.root_folder().rewrite_hosts_files()


def load_custom_attrs_from_mk_file(lock):
    filename = os.path.join(multisite_dir(), "custom_attrs.mk")
    vars_ = store.load_mk_file(
        filename,
        {
            "wato_user_attrs": [],
            "wato_host_attrs": [],
        },
        lock=lock,
    )

    attrs = {}
    for what in ["user", "host"]:
        attributes = vars_.get("wato_%s_attrs" % what, [])
        assert isinstance(attributes, list)
        if what == "host":
            attributes = transform_pre_16_host_topics(attributes)
        attrs[what] = attributes
    return attrs


def save_custom_attrs_to_mk_file(attrs):
    output = wato_fileheader()
    for what in ["user", "host"]:
        if what in attrs and len(attrs[what]) > 0:
            output += f"if type(wato_{what}_attrs) != list:\n    wato_{what}_attrs = []\n"
            output += f"wato_{what}_attrs += {pprint.pformat(attrs[what])}\n\n"

    store.mkdir(multisite_dir())
    store.save_text_to_file(multisite_dir() + "custom_attrs.mk", output)
