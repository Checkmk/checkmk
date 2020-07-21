#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

import inspect
from pathlib import Path


def get_plugin_module_name() -> Optional[str]:
    """find out which module registered the plugin"""
    try:
        calling_from = inspect.stack()[2].filename
    except UnicodeDecodeError:  # calling from precompiled host file
        return None
    return Path(calling_from).stem
