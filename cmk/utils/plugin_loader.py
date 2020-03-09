#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import glob
import importlib


def load_plugins(init_file_path, package_name):
    # type: (str, str) -> None
    plugin_files = sorted(glob.glob(os.path.join(os.path.dirname(init_file_path), "*.py")))
    plugins = [
        os.path.basename(f)[:-3]
        for f in plugin_files
        if not os.path.basename(f)[:-3] in ["__init__", "utils"]
    ]

    for plugin_name in plugins:
        importlib.import_module(package_name + '.' + plugin_name)
