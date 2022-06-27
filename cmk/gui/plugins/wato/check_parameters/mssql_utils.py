#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for MSSQL check parameter module internals"""

from cmk.gui.i18n import _
from cmk.gui.valuespec import TextInput


def mssql_item_spec_instance_tablespace() -> TextInput:
    return TextInput(
        title=_("Instance & tablespace name"),
        help=_("The MSSQL instance name and the tablespace name separated by a space."),
        allow_empty=False,
    )


def mssql_item_spec_instance_database_file() -> TextInput:
    return TextInput(
        title=_("Instance, database & file name"),
        help=_("A combination of the instance, database and (logical) file name."),
        allow_empty=False,
    )
