#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# fmt: off


class Labels(Table):
    __tablename__ = 'labels'

    name = Column(
        'name',
        col_type='string',
        description='The name of the label',
    )
    """The name of the label"""

    value = Column(
        'value',
        col_type='string',
        description='The value of the label',
    )
    """The value of the label"""
