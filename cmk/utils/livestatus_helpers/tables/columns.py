#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# fmt: off


class Columns(Table):
    __tablename__ = 'columns'

    description = Column(
        'description',
        col_type='string',
        description='A description of the column',
    )
    """A description of the column"""

    name = Column(
        'name',
        col_type='string',
        description='The name of the column within the table',
    )
    """The name of the column within the table"""

    table = Column(
        'table',
        col_type='string',
        description='The name of the table',
    )
    """The name of the table"""

    type = Column(
        'type',
        col_type='string',
        description='The data type of the column (int, float, string, list)',
    )
    """The data type of the column (int, float, string, list)"""
