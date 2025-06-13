#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    Float,
    Integer,
    MonitoringState,
    Percentage,
    TextInput,
    Tuple,
)


def _parameter_valuespec_livestatus_status():
    return Dictionary(
        help=_(
            "When monitoring the performance of a monitoring site (i.e. its core) "
            "then also settings are being checked, e.g. for manually disabled notifications. "
            "The status of the various situations can be configured here."
        ),
        elements=[
            (
                "site_stopped",
                MonitoringState(title="State when the site is stopped", default_value=2),
            ),
            (
                "execute_host_checks",
                MonitoringState(title="State when host checks are disabled", default_value=2),
            ),
            (
                "execute_service_checks",
                MonitoringState(title="State when service checks are disabled", default_value=2),
            ),
            (
                "accept_passive_host_checks",
                MonitoringState(
                    title="State when not accepting passive host checks", default_value=2
                ),
            ),
            (
                "accept_passive_service_checks",
                MonitoringState(
                    title="State when not accepting passive service checks", default_value=2
                ),
            ),
            (
                "check_host_freshness",
                MonitoringState(title="State when not checking host freshness", default_value=2),
            ),
            (
                "check_service_freshness",
                MonitoringState(title="State when not checking service freshness", default_value=2),
            ),
            (
                "enable_event_handlers",
                MonitoringState(
                    title="State when alert handlers ('event handlers' when using nagios core) are disabled",
                    default_value=0,
                ),
            ),
            (
                "enable_flap_detection",
                MonitoringState(title="State when flap detection is disabled", default_value=1),
            ),
            (
                "enable_notifications",
                MonitoringState(title="State when notifications are disabled", default_value=2),
            ),
            (
                "process_performance_data",
                MonitoringState(title="State when performance data is disabled", default_value=1),
            ),
            (
                "check_external_commands",
                MonitoringState(title="State when not checking external commands", default_value=2),
            ),
            (
                "site_cert_days",
                Tuple(
                    title=_("Site certificate validity"),
                    help=_("Minimum number of days a certificate has to be valid."),
                    elements=[
                        Integer(
                            title=_("Warning at or below"),
                            minvalue=0,
                            unit=_("days"),
                            default_value=30,
                        ),
                        Integer(
                            title=_("Critical at or below"),
                            minvalue=0,
                            unit=_("days"),
                            default_value=7,
                        ),
                    ],
                ),
            ),
            (
                "average_latency_generic",
                Tuple(
                    title=_("Levels latency check"),
                    help=_("Set levels for the check latency time"),
                    elements=[
                        Age(
                            title=_("Warning at or above"),
                            default_value=30,
                        ),
                        Age(
                            title=_("Critical at or above"),
                            default_value=60,
                        ),
                    ],
                ),
            ),
            (
                "average_latency_cmk",
                Tuple(
                    title=_("Levels latency checker"),
                    help=_("Set levels for the checker latency time"),
                    elements=[
                        Age(
                            title=_("Warning at or above"),
                            default_value=30,
                        ),
                        Age(
                            title=_("Critical at or above"),
                            default_value=60,
                        ),
                    ],
                ),
            ),
            (
                "average_latency_fetcher",
                Tuple(
                    title=_("Levels latency fetcher"),
                    help=_("Set levels for the fetcher latency time"),
                    elements=[
                        Age(
                            title=_("Warning at or above"),
                            default_value=30,
                        ),
                        Age(
                            title=_("Critical at or above"),
                            default_value=60,
                        ),
                    ],
                ),
            ),
            (
                "helper_usage_generic",
                Tuple(
                    title=_("Levels helper usage check"),
                    help=_("Set levels for the check helper usage"),
                    elements=[
                        Percentage(
                            title=_("Warning at or above"),
                            default_value=60,
                        ),
                        Percentage(
                            title=_("Critical at or above"),
                            default_value=90,
                        ),
                    ],
                ),
            ),
            (
                "helper_usage_cmk",
                Tuple(
                    title=_("Levels helper usage Checkmk"),
                    help=_("Set levels for the Checkmk helper usage"),
                    elements=[
                        Percentage(
                            title=_("Warning at or above"),
                            default_value=60,
                        ),
                        Percentage(
                            title=_("Critical at or above"),
                            default_value=90,
                        ),
                    ],
                ),
            ),
            (
                "helper_usage_fetcher",
                Tuple(
                    title=_("Levels helper usage fetcher"),
                    help=_("Set levels for the fetcher helper usage"),
                    elements=[
                        Percentage(
                            title=_("Warning at or above"),
                            default_value=40,
                        ),
                        Percentage(
                            title=_("Critical at or above"),
                            default_value=80,
                        ),
                    ],
                ),
            ),
            (
                "helper_usage_checker",
                Tuple(
                    title=_("Levels helper usage checker"),
                    help=_("Set levels for the checker helper usage"),
                    elements=[
                        Percentage(
                            title=_("Warning at or above"),
                            default_value=40,
                        ),
                        Percentage(
                            title=_("Critical at or above"),
                            default_value=80,
                        ),
                    ],
                ),
            ),
            (
                "livestatus_usage",
                Tuple(
                    title=_("Levels livestatus usage"),
                    help=_("Set levels for the Checkmk livestatus usage"),
                    elements=[
                        Percentage(
                            title=_("Warning at or above"),
                            default_value=80,
                        ),
                        Percentage(
                            title=_("Critical at or above"),
                            default_value=90,
                        ),
                    ],
                ),
            ),
            (
                "livestatus_overflows_rate",
                Tuple(
                    title=_("Levels livestatus overflows"),
                    help=_("Set levels for the Checkmk livestatus overflows"),
                    elements=[
                        Float(
                            title=_("Warning at or above"),
                            unit=_("/s"),
                            default_value=0.01,
                        ),
                        Float(
                            title=_("Critical at or above"),
                            unit=_("/s"),
                            default_value=0.02,
                        ),
                    ],
                ),
            ),
            (
                "levels_hosts",
                Tuple(
                    title=_("Levels hosts"),
                    help=_("Set levels for the number of hosts"),
                    elements=[
                        Integer(
                            title=_("Warning at or above"),
                            unit=_("Hosts"),
                        ),
                        Integer(
                            title=_("Critical at or above"),
                            unit=_("Hosts"),
                        ),
                    ],
                ),
            ),
            (
                "levels_services",
                Tuple(
                    title=_("Levels services"),
                    help=_("Set levels for the number of services"),
                    elements=[
                        Integer(
                            title=_("Warning at or above"),
                            unit=_("Services"),
                        ),
                        Integer(
                            title=_("Critical at or above"),
                            unit=_("Services"),
                        ),
                    ],
                ),
            ),
            (
                "carbon_overflows_rate",
                Tuple(
                    title=_("Carbon overflows rate"),
                    help=_("Rate of performance data loss for carbon"),
                    elements=[
                        Float(
                            title=_("Warning at or above"),
                            unit=_("/s"),
                            default_value=0.01,
                        ),
                        Float(
                            title=_("Critical at or above"),
                            unit=_("/s"),
                            default_value=0.02,
                        ),
                    ],
                ),
            ),
            (
                "carbon_queue_usage",
                Tuple(
                    title=_("Carbon queue usage"),
                    help=_("Carbon queue usage"),
                    elements=[
                        Percentage(
                            title=_("Warning at or above"),
                            unit=_("%"),
                            default_value=60,
                        ),
                        Percentage(
                            title=_("Critical at or above"),
                            unit=_("%"),
                            default_value=80,
                        ),
                    ],
                ),
            ),
            (
                "influxdb_overflows_rate",
                Tuple(
                    title=_("InfluxDB overflows rate"),
                    help=_("Rate of performance data loss for InfluxDB"),
                    elements=[
                        Float(
                            title=_("Warning at or above"),
                            unit=_("/s"),
                            default_value=0.01,
                        ),
                        Float(
                            title=_("Critical at or above"),
                            unit=_("/s"),
                            default_value=0.02,
                        ),
                    ],
                ),
            ),
            (
                "influxdb_queue_usage",
                Tuple(
                    title=_("InfluxDB queue usage"),
                    help=_("InfluxDB queue usage"),
                    elements=[
                        Percentage(
                            title=_("Warning at or above"),
                            unit=_("%"),
                            default_value=60,
                        ),
                        Percentage(
                            title=_("Critical at or above"),
                            unit=_("%"),
                            default_value=80,
                        ),
                    ],
                ),
            ),
            (
                "rrdcached_overflows_rate",
                Tuple(
                    title=_("RRD overflows rate"),
                    help=_("Rate of performance data loss for RRD"),
                    elements=[
                        Float(
                            title=_("Warning at or above"),
                            unit=_("/s"),
                            default_value=0.01,
                        ),
                        Float(
                            title=_("Critical at or above"),
                            unit=_("/s"),
                            default_value=0.02,
                        ),
                    ],
                ),
            ),
            (
                "rrdcached_queue_usage",
                Tuple(
                    title=_("RRD queue usage"),
                    help=_("RRD queue usage"),
                    elements=[
                        Percentage(
                            title=_("Warning at or above"),
                            unit=_("%"),
                            default_value=60,
                        ),
                        Percentage(
                            title=_("Critical at or above"),
                            unit=_("%"),
                            default_value=80,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="livestatus_status",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of the monitoring site"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_livestatus_status,
        title=lambda: _("Checkmk site performance and settings"),
    )
)
