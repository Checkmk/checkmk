#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# fmt: off


class Contactgroups(Table):
    __tablename__ = 'contactgroups'

    alias = Column(
        'alias',
        col_type='string',
        description='An alias of the contact group',
    )
    """An alias of the contact group"""

    members = Column(
        'members',
        col_type='list',
        description='A list of all members of this contactgroup',
    )
    """A list of all members of this contactgroup"""

    name = Column(
        'name',
        col_type='string',
        description='Name of the contact group',
    )
    """Name of the contact group"""
