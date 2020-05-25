#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import imp
import os

from testlib.utils import cmk_path


def import_module(pathname):
    """Return the module loaded from `pathname`.

    `pathname` is a path relative to the top-level directory
    of the repository.

    This function loads the module at `pathname` even if it does not have
    the ".py" extension.

    See Also:
        - `https://mail.python.org/pipermail/python-ideas/2014-December/030265.html`.

    """
    modname = os.path.splitext(os.path.basename(pathname))[0]
    modpath = os.path.join(cmk_path(), pathname)
    try:
        return imp.load_source(modname, modpath)
    finally:
        try:
            os.remove(modpath + "c")
        except OSError:
            pass
