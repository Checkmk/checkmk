#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.livestatus_client.types import Column, DynamicColumn, Table

# fmt: off


class Crashreports(Table):
    __tablename__ = 'crashreports'

    component = Column(
        'component',
        col_type='string',
        description='The component that crashed (gui, agent, check, etc.)',
    )
    """The component that crashed (gui, agent, check, etc.)"""

    id = Column(
        'id',
        col_type='string',
        description='The ID of a crash report',
    )
    """The ID of a crash report"""

    # Dynamic columns are registered in the core via addDynamicColumn and are
    # not listed in livestatus' "columns" table. They are maintained manually
    # in DYNAMIC_COLUMNS in _create_table.py.

    file = DynamicColumn(
        'file',
        col_type='blob',
        description='Files related to the crash report (crash.info, etc.)',
    )
    """Files related to the crash report (crash.info, etc.)"""
