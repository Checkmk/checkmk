#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# fmt: off


class Status(Table):
    __tablename__ = 'status'

    accept_passive_host_checks = Column(
        'accept_passive_host_checks',
        col_type='int',
        description='Whether passive host checks are accepted in general (0/1)',
    )
    """Whether passive host checks are accepted in general (0/1)"""

    accept_passive_service_checks = Column(
        'accept_passive_service_checks',
        col_type='int',
        description='Whether passive service checks are activated in general (0/1)',
    )
    """Whether passive service checks are activated in general (0/1)"""

    average_latency_checker = Column(
        'average_latency_checker',
        col_type='float',
        description='The average latency for executing Check_MK checkers (i.e. the time the start of the execution is behind the schedule)',
    )
    """The average latency for executing Check_MK checkers (i.e. the time the start of the execution is behind the schedule)"""

    average_latency_fetcher = Column(
        'average_latency_fetcher',
        col_type='float',
        description='The average latency for executing Check_MK fetchers (i.e. the time the start of the execution is behind the schedule)',
    )
    """The average latency for executing Check_MK fetchers (i.e. the time the start of the execution is behind the schedule)"""

    average_latency_generic = Column(
        'average_latency_generic',
        col_type='float',
        description='The average latency for executing active checks (i.e. the time the start of the execution is behind the schedule)',
    )
    """The average latency for executing active checks (i.e. the time the start of the execution is behind the schedule)"""

    average_latency_real_time = Column(
        'average_latency_real_time',
        col_type='float',
        description='The average latency for executing real time checks (i.e. the time the start of the execution is behind the schedule)',
    )
    """The average latency for executing real time checks (i.e. the time the start of the execution is behind the schedule)"""

    average_runnable_jobs_checker = Column(
        'average_runnable_jobs_checker',
        col_type='float',
        description='The average count of queued replies which have not yet been delivered to the checker helpers',
    )
    """The average count of queued replies which have not yet been delivered to the checker helpers"""

    average_runnable_jobs_fetcher = Column(
        'average_runnable_jobs_fetcher',
        col_type='float',
        description='The average count of scheduled fetcher jobs which have not yet been processed',
    )
    """The average count of scheduled fetcher jobs which have not yet been processed"""

    cached_log_messages = Column(
        'cached_log_messages',
        col_type='int',
        description='The current number of log messages MK Livestatus keeps in memory',
    )
    """The current number of log messages MK Livestatus keeps in memory"""

    carbon_bytes_sent = Column(
        'carbon_bytes_sent',
        col_type='float',
        description='The number of number of bytes sent over the carbon connections since program start',
    )
    """The number of number of bytes sent over the carbon connections since program start"""

    carbon_bytes_sent_rate = Column(
        'carbon_bytes_sent_rate',
        col_type='float',
        description='The averaged number of number of bytes sent over the carbon connections per second',
    )
    """The averaged number of number of bytes sent over the carbon connections per second"""

    carbon_overflows = Column(
        'carbon_overflows',
        col_type='float',
        description='The number of times a Carbon connection could not send the metrics since program start',
    )
    """The number of times a Carbon connection could not send the metrics since program start"""

    carbon_overflows_rate = Column(
        'carbon_overflows_rate',
        col_type='float',
        description='The averaged number of times a Carbon connection could not send the metrics per second',
    )
    """The averaged number of times a Carbon connection could not send the metrics per second"""

    carbon_queue_usage = Column(
        'carbon_queue_usage',
        col_type='float',
        description='The number of number of elements in the queue / size of the queue since program start',
    )
    """The number of number of elements in the queue / size of the queue since program start"""

    carbon_queue_usage_rate = Column(
        'carbon_queue_usage_rate',
        col_type='float',
        description='The averaged number of number of elements in the queue / size of the queue per second',
    )
    """The averaged number of number of elements in the queue / size of the queue per second"""

    check_external_commands = Column(
        'check_external_commands',
        col_type='int',
        description='Whether Nagios checks for external commands at its command pipe (0/1)',
    )
    """Whether Nagios checks for external commands at its command pipe (0/1)"""

    check_host_freshness = Column(
        'check_host_freshness',
        col_type='int',
        description='Whether host freshness checking is activated in general (0/1)',
    )
    """Whether host freshness checking is activated in general (0/1)"""

    check_service_freshness = Column(
        'check_service_freshness',
        col_type='int',
        description='Whether service freshness checking is activated in general (0/1)',
    )
    """Whether service freshness checking is activated in general (0/1)"""

    connections = Column(
        'connections',
        col_type='float',
        description='The number of client connections to Livestatus since program start',
    )
    """The number of client connections to Livestatus since program start"""

    connections_rate = Column(
        'connections_rate',
        col_type='float',
        description='The averaged number of client connections to Livestatus per second',
    )
    """The averaged number of client connections to Livestatus per second"""

    core_pid = Column(
        'core_pid',
        col_type='int',
        description='The process ID of the monitoring core',
    )
    """The process ID of the monitoring core"""

    edition = Column(
        'edition',
        col_type='string',
        description='The edition of the site',
    )
    """The edition of the site"""

    enable_event_handlers = Column(
        'enable_event_handlers',
        col_type='int',
        description='Whether alert handlers are activated in general (0/1)',
    )
    """Whether alert handlers are activated in general (0/1)"""

    enable_flap_detection = Column(
        'enable_flap_detection',
        col_type='int',
        description='Whether flap detection is activated in general (0/1)',
    )
    """Whether flap detection is activated in general (0/1)"""

    enable_notifications = Column(
        'enable_notifications',
        col_type='int',
        description='Whether notifications are enabled in general (0/1)',
    )
    """Whether notifications are enabled in general (0/1)"""

    execute_host_checks = Column(
        'execute_host_checks',
        col_type='int',
        description='Whether host checks are executed in general (0/1)',
    )
    """Whether host checks are executed in general (0/1)"""

    execute_service_checks = Column(
        'execute_service_checks',
        col_type='int',
        description='Whether active service checks are activated in general (0/1)',
    )
    """Whether active service checks are activated in general (0/1)"""

    external_command_buffer_max = Column(
        'external_command_buffer_max',
        col_type='int',
        description='The maximum number of slots used in the external command buffer',
    )
    """The maximum number of slots used in the external command buffer"""

    external_command_buffer_slots = Column(
        'external_command_buffer_slots',
        col_type='int',
        description='The size of the buffer for the external commands',
    )
    """The size of the buffer for the external commands"""

    external_command_buffer_usage = Column(
        'external_command_buffer_usage',
        col_type='int',
        description='The number of slots in use of the external command buffer',
    )
    """The number of slots in use of the external command buffer"""

    external_commands = Column(
        'external_commands',
        col_type='float',
        description='The number of external commands since program start',
    )
    """The number of external commands since program start"""

    external_commands_rate = Column(
        'external_commands_rate',
        col_type='float',
        description='The averaged number of external commands per second',
    )
    """The averaged number of external commands per second"""

    forks = Column(
        'forks',
        col_type='float',
        description='The number of process creations since program start',
    )
    """The number of process creations since program start"""

    forks_rate = Column(
        'forks_rate',
        col_type='float',
        description='The averaged number of process creations per second',
    )
    """The averaged number of process creations per second"""

    has_event_handlers = Column(
        'has_event_handlers',
        col_type='int',
        description='Whether or not at alert handler rules are configured (0/1)',
    )
    """Whether or not at alert handler rules are configured (0/1)"""

    helper_usage_checker = Column(
        'helper_usage_checker',
        col_type='float',
        description='The average usage of the checker helpers, ranging from 0.0 (0%) up to 1.0 (100%)',
    )
    """The average usage of the checker helpers, ranging from 0.0 (0%) up to 1.0 (100%)"""

    helper_usage_fetcher = Column(
        'helper_usage_fetcher',
        col_type='float',
        description='The average usage of the fetcher helpers, ranging from 0.0 (0%) up to 1.0 (100%)',
    )
    """The average usage of the fetcher helpers, ranging from 0.0 (0%) up to 1.0 (100%)"""

    helper_usage_generic = Column(
        'helper_usage_generic',
        col_type='float',
        description='The average usage of the active check helpers, ranging from 0.0 (0%) up to 1.0 (100%)',
    )
    """The average usage of the active check helpers, ranging from 0.0 (0%) up to 1.0 (100%)"""

    helper_usage_real_time = Column(
        'helper_usage_real_time',
        col_type='float',
        description='The average usage of the real time check helpers, ranging from 0.0 (0%) up to 1.0 (100%)',
    )
    """The average usage of the real time check helpers, ranging from 0.0 (0%) up to 1.0 (100%)"""

    host_checks = Column(
        'host_checks',
        col_type='float',
        description='The number of host checks since program start',
    )
    """The number of host checks since program start"""

    host_checks_rate = Column(
        'host_checks_rate',
        col_type='float',
        description='The averaged number of host checks per second',
    )
    """The averaged number of host checks per second"""

    influxdb_bytes_sent = Column(
        'influxdb_bytes_sent',
        col_type='float',
        description='The number of number of bytes sent over the InfluxDB connections (payload only) since program start',
    )
    """The number of number of bytes sent over the InfluxDB connections (payload only) since program start"""

    influxdb_bytes_sent_rate = Column(
        'influxdb_bytes_sent_rate',
        col_type='float',
        description='The averaged number of number of bytes sent over the InfluxDB connections (payload only) per second',
    )
    """The averaged number of number of bytes sent over the InfluxDB connections (payload only) per second"""

    influxdb_overflows = Column(
        'influxdb_overflows',
        col_type='float',
        description='The number of times an InfluxDB connection could not send the metrics since program start',
    )
    """The number of times an InfluxDB connection could not send the metrics since program start"""

    influxdb_overflows_rate = Column(
        'influxdb_overflows_rate',
        col_type='float',
        description='The averaged number of times an InfluxDB connection could not send the metrics per second',
    )
    """The averaged number of times an InfluxDB connection could not send the metrics per second"""

    influxdb_queue_usage = Column(
        'influxdb_queue_usage',
        col_type='float',
        description='The number of number of elements in the queue / size of the queue since program start',
    )
    """The number of number of elements in the queue / size of the queue since program start"""

    influxdb_queue_usage_rate = Column(
        'influxdb_queue_usage_rate',
        col_type='float',
        description='The averaged number of number of elements in the queue / size of the queue per second',
    )
    """The averaged number of number of elements in the queue / size of the queue per second"""

    interval_length = Column(
        'interval_length',
        col_type='int',
        description='The default interval length',
    )
    """The default interval length"""

    last_command_check = Column(
        'last_command_check',
        col_type='time',
        description='Time of the last check for a command as UNIX timestamp',
    )
    """Time of the last check for a command as UNIX timestamp"""

    last_log_rotation = Column(
        'last_log_rotation',
        col_type='time',
        description='Time time of the last log file rotation',
    )
    """Time time of the last log file rotation"""

    license_usage_history = Column(
        'license_usage_history',
        col_type='blob',
        description='Historic license usage information',
    )
    """Historic license usage information"""

    livechecks = Column(
        'livechecks',
        col_type='float',
        description='The number of checks executed via livecheck since program start',
    )
    """The number of checks executed via livecheck since program start"""

    livechecks_rate = Column(
        'livechecks_rate',
        col_type='float',
        description='The averaged number of checks executed via livecheck per second',
    )
    """The averaged number of checks executed via livecheck per second"""

    livestatus_active_connections = Column(
        'livestatus_active_connections',
        col_type='int',
        description='The current number of active connections to MK Livestatus',
    )
    """The current number of active connections to MK Livestatus"""

    livestatus_overflows = Column(
        'livestatus_overflows',
        col_type='float',
        description='The number of times a Livestatus connection could not be immediately accepted because all threads where busy since program start',
    )
    """The number of times a Livestatus connection could not be immediately accepted because all threads where busy since program start"""

    livestatus_overflows_rate = Column(
        'livestatus_overflows_rate',
        col_type='float',
        description='The averaged number of times a Livestatus connection could not be immediately accepted because all threads where busy per second',
    )
    """The averaged number of times a Livestatus connection could not be immediately accepted because all threads where busy per second"""

    livestatus_queued_connections = Column(
        'livestatus_queued_connections',
        col_type='int',
        description='The current number of queued connections to MK Livestatus',
    )
    """The current number of queued connections to MK Livestatus"""

    livestatus_threads = Column(
        'livestatus_threads',
        col_type='int',
        description='The maximum number of connections to MK Livestatus that can be handled in parallel',
    )
    """The maximum number of connections to MK Livestatus that can be handled in parallel"""

    livestatus_usage = Column(
        'livestatus_usage',
        col_type='float',
        description='The average usage of the livestatus connection slots, ranging from 0.0 (0%) up to 1.0 (100%)',
    )
    """The average usage of the livestatus connection slots, ranging from 0.0 (0%) up to 1.0 (100%)"""

    livestatus_version = Column(
        'livestatus_version',
        col_type='string',
        description='The version of the MK Livestatus module',
    )
    """The version of the MK Livestatus module"""

    log_messages = Column(
        'log_messages',
        col_type='float',
        description='The number of new log messages since program start',
    )
    """The number of new log messages since program start"""

    log_messages_rate = Column(
        'log_messages_rate',
        col_type='float',
        description='The averaged number of new log messages per second',
    )
    """The averaged number of new log messages per second"""

    max_long_output_size = Column(
        'max_long_output_size',
        col_type='int',
        description='Maximum length of long output',
    )
    """Maximum length of long output"""

    metrics_count = Column(
        'metrics_count',
        col_type='float',
        description='The number of number of metrics processed by the core since program start',
    )
    """The number of number of metrics processed by the core since program start"""

    metrics_count_rate = Column(
        'metrics_count_rate',
        col_type='float',
        description='The averaged number of number of metrics processed by the core per second',
    )
    """The averaged number of number of metrics processed by the core per second"""

    mk_inventory_last = Column(
        'mk_inventory_last',
        col_type='time',
        description='The timestamp of the last time a host has been inventorized by Check_MK HW/SW Inventory',
    )
    """The timestamp of the last time a host has been inventorized by Check_MK HW/SW Inventory"""

    nagios_pid = Column(
        'nagios_pid',
        col_type='int',
        description='The process ID of the monitoring core',
    )
    """The process ID of the monitoring core"""

    neb_callbacks = Column(
        'neb_callbacks',
        col_type='float',
        description='The number of NEB callbacks since program start',
    )
    """The number of NEB callbacks since program start"""

    neb_callbacks_rate = Column(
        'neb_callbacks_rate',
        col_type='float',
        description='The averaged number of NEB callbacks per second',
    )
    """The averaged number of NEB callbacks per second"""

    num_hosts = Column(
        'num_hosts',
        col_type='int',
        description='The total number of hosts',
    )
    """The total number of hosts"""

    num_queued_alerts = Column(
        'num_queued_alerts',
        col_type='int',
        description='The number of queued alerts which have not yet been delivered to the alert helper',
    )
    """The number of queued alerts which have not yet been delivered to the alert helper"""

    num_queued_notifications = Column(
        'num_queued_notifications',
        col_type='int',
        description='The number of queued notifications which have not yet been delivered to the notification helper',
    )
    """The number of queued notifications which have not yet been delivered to the notification helper"""

    num_services = Column(
        'num_services',
        col_type='int',
        description='The total number of services',
    )
    """The total number of services"""

    obsess_over_hosts = Column(
        'obsess_over_hosts',
        col_type='int',
        description='Whether Nagios will obsess over host checks (0/1)',
    )
    """Whether Nagios will obsess over host checks (0/1)"""

    obsess_over_services = Column(
        'obsess_over_services',
        col_type='int',
        description='Whether Nagios will obsess over service checks and run the ocsp_command (0/1)',
    )
    """Whether Nagios will obsess over service checks and run the ocsp_command (0/1)"""

    perf_data_count = Column(
        'perf_data_count',
        col_type='float',
        description='The number of number of performance data processed by the core since program start',
    )
    """The number of number of performance data processed by the core since program start"""

    perf_data_count_rate = Column(
        'perf_data_count_rate',
        col_type='float',
        description='The averaged number of number of performance data processed by the core per second',
    )
    """The averaged number of number of performance data processed by the core per second"""

    process_performance_data = Column(
        'process_performance_data',
        col_type='int',
        description='Whether processing of performance data is activated in general (0/1)',
    )
    """Whether processing of performance data is activated in general (0/1)"""

    program_start = Column(
        'program_start',
        col_type='time',
        description='Time of the last program start or configuration reload as UNIX timestamp',
    )
    """Time of the last program start or configuration reload as UNIX timestamp"""

    program_version = Column(
        'program_version',
        col_type='string',
        description='The version of the monitoring daemon',
    )
    """The version of the monitoring daemon"""

    requests = Column(
        'requests',
        col_type='float',
        description='The number of requests to Livestatus since program start',
    )
    """The number of requests to Livestatus since program start"""

    requests_rate = Column(
        'requests_rate',
        col_type='float',
        description='The averaged number of requests to Livestatus per second',
    )
    """The averaged number of requests to Livestatus per second"""

    rrdcached_bytes_sent = Column(
        'rrdcached_bytes_sent',
        col_type='float',
        description='The number of number of bytes sent over to the RRDs since program start',
    )
    """The number of number of bytes sent over to the RRDs since program start"""

    rrdcached_bytes_sent_rate = Column(
        'rrdcached_bytes_sent_rate',
        col_type='float',
        description='The averaged number of number of bytes sent over to the RRDs per second',
    )
    """The averaged number of number of bytes sent over to the RRDs per second"""

    rrdcached_overflows = Column(
        'rrdcached_overflows',
        col_type='float',
        description='The number of times an RRDCacheD connection could not send the metrics since program start',
    )
    """The number of times an RRDCacheD connection could not send the metrics since program start"""

    rrdcached_overflows_rate = Column(
        'rrdcached_overflows_rate',
        col_type='float',
        description='The averaged number of times an RRDCacheD connection could not send the metrics per second',
    )
    """The averaged number of times an RRDCacheD connection could not send the metrics per second"""

    rrdcached_queue_usage = Column(
        'rrdcached_queue_usage',
        col_type='float',
        description='The number of number of elements in the queue / size of the queue since program start',
    )
    """The number of number of elements in the queue / size of the queue since program start"""

    rrdcached_queue_usage_rate = Column(
        'rrdcached_queue_usage_rate',
        col_type='float',
        description='The averaged number of number of elements in the queue / size of the queue per second',
    )
    """The averaged number of number of elements in the queue / size of the queue per second"""

    service_checks = Column(
        'service_checks',
        col_type='float',
        description='The number of completed service checks since program start',
    )
    """The number of completed service checks since program start"""

    service_checks_rate = Column(
        'service_checks_rate',
        col_type='float',
        description='The averaged number of completed service checks per second',
    )
    """The averaged number of completed service checks per second"""

    state_file_created = Column(
        'state_file_created',
        col_type='time',
        description='The time when state file had been created',
    )
    """The time when state file had been created"""
