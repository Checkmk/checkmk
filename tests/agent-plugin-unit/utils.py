#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys


def plugin_path():
    return "/plugins"


def import_module(modpath):
    """Return the module loaded from `modpath`.

    `modpath` is the relative path to the `plugin_path` (see above)

    This function loads the module at `modpath` even if it does not have
    the ".py" extension.

    See Also:
        - `https://mail.python.org/pipermail/python-ideas/2014-December/030265.html`.
    """
    modpath = os.path.join(plugin_path(), modpath)
    modname = os.path.splitext(os.path.basename(modpath))[0]

    # Python 2.6: Use the previously generated .py2 agent plugin
    if sys.version_info <= (2, 7):
        modpath = os.path.splitext(modpath)[0] + "_2.py"

    if sys.version_info[0] >= 3:
        import importlib  # pylint: disable=import-outside-toplevel

        return importlib.machinery.SourceFileLoader(modname, modpath).load_module()  # type: ignore[call-arg]  # pylint: disable=no-value-for-parameter,deprecated-method

    import imp  # pylint: disable=import-outside-toplevel, deprecated-module

    try:
        return imp.load_source(modname, modpath)
    finally:
        try:
            os.remove(modpath + "c")
        except OSError:
            pass
