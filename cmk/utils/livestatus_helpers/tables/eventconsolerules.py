#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# fmt: off


class Eventconsolerules(Table):
    __tablename__ = 'eventconsolerules'

    rule_hits = Column(
        'rule_hits',
        col_type='int',
        description='The times rule matched an incoming message',
    )
    """The times rule matched an incoming message"""

    rule_id = Column(
        'rule_id',
        col_type='string',
        description='The ID of the rule',
    )
    """The ID of the rule"""
