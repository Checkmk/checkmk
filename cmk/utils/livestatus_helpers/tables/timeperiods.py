#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# fmt: off


class Timeperiods(Table):
    __tablename__ = 'timeperiods'

    alias = Column(
        'alias',
        col_type='string',
        description='The alias of the timeperiod',
    )
    """The alias of the timeperiod"""

    in_ = Column(
        'in',
        col_type='int',
        description='Wether we are currently in this period (0/1)',
    )
    """Wether we are currently in this period (0/1)"""

    name = Column(
        'name',
        col_type='string',
        description='The name of the timeperiod',
    )
    """The name of the timeperiod"""

    next_transition = Column(
        'next_transition',
        col_type='time',
        description='Time of the next transition. 0 if there is no further transition.',
    )
    """Time of the next transition. 0 if there is no further transition."""

    next_transition_id = Column(
        'next_transition_id',
        col_type='int',
        description='The index of the next transition',
    )
    """The index of the next transition"""

    num_transitions = Column(
        'num_transitions',
        col_type='int',
        description='The total number of computed transitions from 0->1 or 1->0',
    )
    """The total number of computed transitions from 0->1 or 1->0"""

    transitions = Column(
        'transitions',
        col_type='list',
        description='The list of future transitions of the timeperiod (only CMC)',
    )
    """The list of future transitions of the timeperiod (only CMC)"""
