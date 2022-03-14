#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import pprint

from cmk.utils import store

from cmk.gui import userdb, watolib
from cmk.gui.config import load_config
from cmk.gui.watolib import Folder
from cmk.gui.watolib.host_attributes import transform_pre_16_host_topics


def update_user_custom_attrs():
    userdb.update_config_based_user_attributes()
    userdb.rewrite_users()


def update_host_custom_attrs():
    load_config()
    Folder.invalidate_caches()
    Folder.root_folder().rewrite_hosts_files()


def load_custom_attrs_from_mk_file(lock):
    filename = os.path.join(watolib.multisite_dir(), "custom_attrs.mk")
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
        if what == "host":
            attributes = transform_pre_16_host_topics(attributes)
        attrs[what] = attributes
    return attrs


def save_custom_attrs_to_mk_file(attrs):
    output = watolib.wato_fileheader()
    for what in ["user", "host"]:
        if what in attrs and len(attrs[what]) > 0:
            output += "if type(wato_%s_attrs) != list:\n    wato_%s_attrs = []\n" % (what, what)
            output += "wato_%s_attrs += %s\n\n" % (what, pprint.pformat(attrs[what]))

    store.mkdir(watolib.multisite_dir())
    store.save_text_to_file(watolib.multisite_dir() + "custom_attrs.mk", output)
