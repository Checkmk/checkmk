#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# fmt: off


class Commands(Table):
    __tablename__ = 'commands'

    line = Column(
        'line',
        col_type='string',
        description='The shell command line',
    )
    """The shell command line"""

    name = Column(
        'name',
        col_type='string',
        description='The name of the command',
    )
    """The name of the command"""
