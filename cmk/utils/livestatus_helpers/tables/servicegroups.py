#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# yapf: disable


class Servicegroups(Table):
    __tablename__ = 'servicegroups'

    action_url = Column(
        'action_url',
        col_type='string',
        description='An optional URL to custom notes or actions on the service group',
    )
    """An optional URL to custom notes or actions on the service group"""

    alias = Column(
        'alias',
        col_type='string',
        description='An alias of the servicegroup',
    )
    """An alias of the servicegroup"""

    members = Column(
        'members',
        col_type='list',
        description='A list of all members of the service group as host/service pairs',
    )
    """A list of all members of the service group as host/service pairs"""

    members_with_state = Column(
        'members_with_state',
        col_type='list',
        description='A list of all members of the service group with state and has_been_checked',
    )
    """A list of all members of the service group with state and has_been_checked"""

    name = Column(
        'name',
        col_type='string',
        description='Name of the servicegroup',
    )
    """Name of the servicegroup"""

    notes = Column(
        'notes',
        col_type='string',
        description='Optional additional notes about the service group',
    )
    """Optional additional notes about the service group"""

    notes_url = Column(
        'notes_url',
        col_type='string',
        description='An optional URL to further notes on the service group',
    )
    """An optional URL to further notes on the service group"""

    num_services = Column(
        'num_services',
        col_type='int',
        description='The total number of services in the group',
    )
    """The total number of services in the group"""

    num_services_crit = Column(
        'num_services_crit',
        col_type='int',
        description='The number of services in the group that are CRIT',
    )
    """The number of services in the group that are CRIT"""

    num_services_handled_problems = Column(
        'num_services_handled_problems',
        col_type='int',
        description='The number of services in the group that have handled problems',
    )
    """The number of services in the group that have handled problems"""

    num_services_hard_crit = Column(
        'num_services_hard_crit',
        col_type='int',
        description='The number of services in the group that are CRIT',
    )
    """The number of services in the group that are CRIT"""

    num_services_hard_ok = Column(
        'num_services_hard_ok',
        col_type='int',
        description='The number of services in the group that are OK',
    )
    """The number of services in the group that are OK"""

    num_services_hard_unknown = Column(
        'num_services_hard_unknown',
        col_type='int',
        description='The number of services in the group that are UNKNOWN',
    )
    """The number of services in the group that are UNKNOWN"""

    num_services_hard_warn = Column(
        'num_services_hard_warn',
        col_type='int',
        description='The number of services in the group that are WARN',
    )
    """The number of services in the group that are WARN"""

    num_services_ok = Column(
        'num_services_ok',
        col_type='int',
        description='The number of services in the group that are OK',
    )
    """The number of services in the group that are OK"""

    num_services_pending = Column(
        'num_services_pending',
        col_type='int',
        description='The number of services in the group that are PENDING',
    )
    """The number of services in the group that are PENDING"""

    num_services_unhandled_problems = Column(
        'num_services_unhandled_problems',
        col_type='int',
        description='The number of services in the group that have unhandled problems',
    )
    """The number of services in the group that have unhandled problems"""

    num_services_unknown = Column(
        'num_services_unknown',
        col_type='int',
        description='The number of services in the group that are UNKNOWN',
    )
    """The number of services in the group that are UNKNOWN"""

    num_services_warn = Column(
        'num_services_warn',
        col_type='int',
        description='The number of services in the group that are WARN',
    )
    """The number of services in the group that are WARN"""

    worst_service_state = Column(
        'worst_service_state',
        col_type='int',
        description='The worst soft state of all of the groups services (OK <= WARN <= UNKNOWN <= CRIT)',
    )
    """The worst soft state of all of the groups services (OK <= WARN <= UNKNOWN <= CRIT)"""
