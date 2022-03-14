#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# yapf: disable


class Hostgroups(Table):
    __tablename__ = 'hostgroups'

    action_url = Column(
        'action_url',
        col_type='string',
        description='An optional URL to custom notes or actions on the host group',
    )
    """An optional URL to custom notes or actions on the host group"""

    alias = Column(
        'alias',
        col_type='string',
        description='An alias of the hostgroup',
    )
    """An alias of the hostgroup"""

    members = Column(
        'members',
        col_type='list',
        description='A list of all host names that are members of the hostgroup',
    )
    """A list of all host names that are members of the hostgroup"""

    members_with_state = Column(
        'members_with_state',
        col_type='list',
        description='A list of all host names that are members of the hostgroup together with state and has_been_checked',
    )
    """A list of all host names that are members of the hostgroup together with state and has_been_checked"""

    name = Column(
        'name',
        col_type='string',
        description='Name of the hostgroup',
    )
    """Name of the hostgroup"""

    notes = Column(
        'notes',
        col_type='string',
        description='Optional additional notes about the host group',
    )
    """Optional additional notes about the host group"""

    notes_url = Column(
        'notes_url',
        col_type='string',
        description='An optional URL to further notes on the host group',
    )
    """An optional URL to further notes on the host group"""

    num_hosts = Column(
        'num_hosts',
        col_type='int',
        description='The total number of hosts in the group',
    )
    """The total number of hosts in the group"""

    num_hosts_down = Column(
        'num_hosts_down',
        col_type='int',
        description='The number of hosts in the group that are down',
    )
    """The number of hosts in the group that are down"""

    num_hosts_handled_problems = Column(
        'num_hosts_handled_problems',
        col_type='int',
        description='The total number of hosts in this group with handled problems',
    )
    """The total number of hosts in this group with handled problems"""

    num_hosts_pending = Column(
        'num_hosts_pending',
        col_type='int',
        description='The number of hosts in the group that are pending',
    )
    """The number of hosts in the group that are pending"""

    num_hosts_unhandled_problems = Column(
        'num_hosts_unhandled_problems',
        col_type='int',
        description='The total number of hosts in this group with unhandled problems',
    )
    """The total number of hosts in this group with unhandled problems"""

    num_hosts_unreach = Column(
        'num_hosts_unreach',
        col_type='int',
        description='The number of hosts in the group that are unreachable',
    )
    """The number of hosts in the group that are unreachable"""

    num_hosts_up = Column(
        'num_hosts_up',
        col_type='int',
        description='The number of hosts in the group that are up',
    )
    """The number of hosts in the group that are up"""

    num_services = Column(
        'num_services',
        col_type='int',
        description='The total number of services of hosts in this group',
    )
    """The total number of services of hosts in this group"""

    num_services_crit = Column(
        'num_services_crit',
        col_type='int',
        description='The total number of services with the state CRIT of hosts in this group',
    )
    """The total number of services with the state CRIT of hosts in this group"""

    num_services_handled_problems = Column(
        'num_services_handled_problems',
        col_type='int',
        description='The total number of services of hosts in this group with handled problems',
    )
    """The total number of services of hosts in this group with handled problems"""

    num_services_hard_crit = Column(
        'num_services_hard_crit',
        col_type='int',
        description='The total number of services with the state CRIT of hosts in this group',
    )
    """The total number of services with the state CRIT of hosts in this group"""

    num_services_hard_ok = Column(
        'num_services_hard_ok',
        col_type='int',
        description='The total number of services with the state OK of hosts in this group',
    )
    """The total number of services with the state OK of hosts in this group"""

    num_services_hard_unknown = Column(
        'num_services_hard_unknown',
        col_type='int',
        description='The total number of services with the state UNKNOWN of hosts in this group',
    )
    """The total number of services with the state UNKNOWN of hosts in this group"""

    num_services_hard_warn = Column(
        'num_services_hard_warn',
        col_type='int',
        description='The total number of services with the state WARN of hosts in this group',
    )
    """The total number of services with the state WARN of hosts in this group"""

    num_services_ok = Column(
        'num_services_ok',
        col_type='int',
        description='The total number of services with the state OK of hosts in this group',
    )
    """The total number of services with the state OK of hosts in this group"""

    num_services_pending = Column(
        'num_services_pending',
        col_type='int',
        description='The total number of services with the state Pending of hosts in this group',
    )
    """The total number of services with the state Pending of hosts in this group"""

    num_services_unhandled_problems = Column(
        'num_services_unhandled_problems',
        col_type='int',
        description='The total number of services of hosts in this group with unhandled problems',
    )
    """The total number of services of hosts in this group with unhandled problems"""

    num_services_unknown = Column(
        'num_services_unknown',
        col_type='int',
        description='The total number of services with the state UNKNOWN of hosts in this group',
    )
    """The total number of services with the state UNKNOWN of hosts in this group"""

    num_services_warn = Column(
        'num_services_warn',
        col_type='int',
        description='The total number of services with the state WARN of hosts in this group',
    )
    """The total number of services with the state WARN of hosts in this group"""

    worst_host_state = Column(
        'worst_host_state',
        col_type='int',
        description='The worst state of all of the groups\' hosts (UP <= UNREACHABLE <= DOWN)',
    )
    """The worst state of all of the groups' hosts (UP <= UNREACHABLE <= DOWN)"""

    worst_service_hard_state = Column(
        'worst_service_hard_state',
        col_type='int',
        description='The worst state of all services that belong to a host of this group (OK <= WARN <= UNKNOWN <= CRIT)',
    )
    """The worst state of all services that belong to a host of this group (OK <= WARN <= UNKNOWN <= CRIT)"""

    worst_service_state = Column(
        'worst_service_state',
        col_type='int',
        description='The worst state of all services that belong to a host of this group (OK <= WARN <= UNKNOWN <= CRIT)',
    )
    """The worst state of all services that belong to a host of this group (OK <= WARN <= UNKNOWN <= CRIT)"""
