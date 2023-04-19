#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# fmt: off


class Eventconsolestatus(Table):
    __tablename__ = 'eventconsolestatus'

    status_average_connect_rate = Column(
        'status_average_connect_rate',
        col_type='float',
        description='The average connect rate',
    )
    """The average connect rate"""

    status_average_drop_rate = Column(
        'status_average_drop_rate',
        col_type='float',
        description='The average drop rate',
    )
    """The average drop rate"""

    status_average_event_rate = Column(
        'status_average_event_rate',
        col_type='float',
        description='The average event rate',
    )
    """The average event rate"""

    status_average_message_rate = Column(
        'status_average_message_rate',
        col_type='float',
        description='The average incoming message rate',
    )
    """The average incoming message rate"""

    status_average_overflow_rate = Column(
        'status_average_overflow_rate',
        col_type='float',
        description='The average overflow rate',
    )
    """The average overflow rate"""

    status_average_processing_time = Column(
        'status_average_processing_time',
        col_type='float',
        description='The average incoming message processing time',
    )
    """The average incoming message processing time"""

    status_average_request_time = Column(
        'status_average_request_time',
        col_type='float',
        description='The average status client request time',
    )
    """The average status client request time"""

    status_average_rule_hit_rate = Column(
        'status_average_rule_hit_rate',
        col_type='float',
        description='The average rule hit rate',
    )
    """The average rule hit rate"""

    status_average_rule_trie_rate = Column(
        'status_average_rule_trie_rate',
        col_type='float',
        description='The average rule trie rate',
    )
    """The average rule trie rate"""

    status_average_sync_time = Column(
        'status_average_sync_time',
        col_type='float',
        description='The average sync time',
    )
    """The average sync time"""

    status_config_load_time = Column(
        'status_config_load_time',
        col_type='int',
        description='The time when the Event Console config was loaded',
    )
    """The time when the Event Console config was loaded"""

    status_connect_rate = Column(
        'status_connect_rate',
        col_type='float',
        description='The connect rate',
    )
    """The connect rate"""

    status_connects = Column(
        'status_connects',
        col_type='int',
        description='The number of connects',
    )
    """The number of connects"""

    status_drop_rate = Column(
        'status_drop_rate',
        col_type='float',
        description='The drop rate',
    )
    """The drop rate"""

    status_drops = Column(
        'status_drops',
        col_type='int',
        description='The number of message drops (decided by a rule) since startup of the Event Console',
    )
    """The number of message drops (decided by a rule) since startup of the Event Console"""

    status_event_limit_active_hosts = Column(
        'status_event_limit_active_hosts',
        col_type='list',
        description='List of host names with active event limit',
    )
    """List of host names with active event limit"""

    status_event_limit_active_overall = Column(
        'status_event_limit_active_overall',
        col_type='int',
        description='Whether or not the overall event limit is in effect (0/1)',
    )
    """Whether or not the overall event limit is in effect (0/1)"""

    status_event_limit_active_rules = Column(
        'status_event_limit_active_rules',
        col_type='list',
        description='List of rule IDs which rules event limit is active',
    )
    """List of rule IDs which rules event limit is active"""

    status_event_limit_host = Column(
        'status_event_limit_host',
        col_type='int',
        description='The currently active event limit for hosts',
    )
    """The currently active event limit for hosts"""

    status_event_limit_overall = Column(
        'status_event_limit_overall',
        col_type='int',
        description='The currently active event limit for all events',
    )
    """The currently active event limit for all events"""

    status_event_limit_rule = Column(
        'status_event_limit_rule',
        col_type='int',
        description='The currently active event limit for rules',
    )
    """The currently active event limit for rules"""

    status_event_rate = Column(
        'status_event_rate',
        col_type='float',
        description='The event rate',
    )
    """The event rate"""

    status_events = Column(
        'status_events',
        col_type='int',
        description='The number of events received since startup of the Event Console',
    )
    """The number of events received since startup of the Event Console"""

    status_message_rate = Column(
        'status_message_rate',
        col_type='float',
        description='The incoming message rate',
    )
    """The incoming message rate"""

    status_messages = Column(
        'status_messages',
        col_type='int',
        description='The number of messages received since startup of the Event Console',
    )
    """The number of messages received since startup of the Event Console"""

    status_num_open_events = Column(
        'status_num_open_events',
        col_type='int',
        description='The number of currently open events',
    )
    """The number of currently open events"""

    status_overflow_rate = Column(
        'status_overflow_rate',
        col_type='float',
        description='The overflow rate',
    )
    """The overflow rate"""

    status_overflows = Column(
        'status_overflows',
        col_type='int',
        description='The number of message overflows, i.e. messages simply dropped due to an overflow of the Event Console',
    )
    """The number of message overflows, i.e. messages simply dropped due to an overflow of the Event Console"""

    status_replication_last_sync = Column(
        'status_replication_last_sync',
        col_type='time',
        description='Time of the last replication (Unix timestamp)',
    )
    """Time of the last replication (Unix timestamp)"""

    status_replication_slavemode = Column(
        'status_replication_slavemode',
        col_type='string',
        description='The replication slavemode (empty or one of sync/takeover)',
    )
    """The replication slavemode (empty or one of sync/takeover)"""

    status_replication_success = Column(
        'status_replication_success',
        col_type='int',
        description='Whether the replication succeeded (0/1)',
    )
    """Whether the replication succeeded (0/1)"""

    status_rule_hit_rate = Column(
        'status_rule_hit_rate',
        col_type='float',
        description='The rule hit rate',
    )
    """The rule hit rate"""

    status_rule_hits = Column(
        'status_rule_hits',
        col_type='int',
        description='The number of rule hits since startup of the Event Console',
    )
    """The number of rule hits since startup of the Event Console"""

    status_rule_trie_rate = Column(
        'status_rule_trie_rate',
        col_type='float',
        description='The rule trie rate',
    )
    """The rule trie rate"""

    status_rule_tries = Column(
        'status_rule_tries',
        col_type='int',
        description='The number of rule tries',
    )
    """The number of rule tries"""

    status_virtual_memory_size = Column(
        'status_virtual_memory_size',
        col_type='int',
        description='The current virtual memory size in bytes',
    )
    """The current virtual memory size in bytes"""
