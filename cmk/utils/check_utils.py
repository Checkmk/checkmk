#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def section_name_of(check_plugin_name: str) -> str:
    return check_plugin_name.split(".")[0]


def maincheckify(subcheck_name: str) -> str:
    """Get new plugin name

    The new API does not know about "subchecks", so drop the dot notation.
    The validation step will prevent us from having colliding plugins.
    """
    return (subcheck_name.replace('.', '_')  # subchecks don't exist anymore
            .replace('-', '_')  # "sap.value-groups"
           )
