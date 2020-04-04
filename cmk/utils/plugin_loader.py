#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Tuple, Generator  # pylint: disable=unused-import

import sys
import importlib
import itertools

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=unused-import
else:
    from pathlib2 import Path  # pylint: disable=unused-import


def load_plugins_with_exceptions(package_name, *init_file_paths):
    # type: (str, Path) -> Generator[Tuple[str, Exception], None, None]
    plugin_files = itertools.chain(*(pth.glob("*.py") for pth in init_file_paths))
    plugins = set(fn.stem for fn in plugin_files) - {"__init__", "utils"}

    for plugin_name in sorted(plugins):
        try:
            importlib.import_module("%s.%s" % (package_name, plugin_name))
        except Exception as exc:
            yield package_name, exc


def load_plugins(init_file_path, package_name):
    # type: (str, str) -> None
    for _name, exc in load_plugins_with_exceptions(package_name, Path(init_file_path).parent):
        raise exc
