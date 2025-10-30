#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.graphing.v1 import Title, graphs, metrics, perfometers

#
# unit definitions
#
UNIT_DBM = metrics.Unit(metrics.DecimalNotation('dBm'))
UNIT_HZ = metrics.Unit(metrics.SINotation('hZ'))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(''))
UNIT_PERCENT = metrics.Unit(metrics.DecimalNotation('%'))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
#
# license overview
#
metric_sum_licensed_devices = metrics.Metric(
    name='sum_licensed_devices',
    title=Title('Licensed devices'),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_remaining_time = metrics.Metric(
    name='remaining_time',
    title=Title('Remaining time'),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

graph_cisco_meraki_remaining_time = graphs.Graph(
    name='cisco_meraki.remaining_time',
    title=Title('Cisco Meraki Licenses remaining time'),
    compound_lines=['remaining_time'],
    simple_lines=[
        metrics.WarningOf("remaining_time"),
        metrics.CriticalOf("remaining_time"),
    ],
    minimal_range=graphs.MinimalRange(0, 180),
)

graph_cisco_meraki_licensed_devices = graphs.Graph(
    name='cisco_meraki_licensed_devices',
    title=Title('Cisco Meraki Licensed devices'),
    compound_lines=['sum_licensed_devices'],
    minimal_range=graphs.MinimalRange(0, 10),
)

perfometer_licensing = perfometers.Stacked(
    name="merak_licensing",
    # upper and lower are in the wrong order
    lower=perfometers.Perfometer(
        name='sum_licensed_devices',
        focus_range=perfometers.FocusRange(perfometers.Open(0), perfometers.Open(100)),
        segments=['sum_licensed_devices'],
    ),
    upper=perfometers.Perfometer(
        name='remaining_time',
        focus_range=perfometers.FocusRange(perfometers.Open(0), perfometers.Open(180)),
        segments=["remaining_time"],
    ),
)

#
# wireless devices status
#
metric_signal_power = metrics.Metric(
    name='signal_power',
    title=Title("Power"),
    unit=UNIT_DBM,
    color=metrics.Color.GREEN,
)

metric_channel_width = metrics.Metric(
    name="channel_width",
    title=Title("Channel Width"),
    unit=UNIT_HZ,
    color=metrics.Color.BLUE,
)

metric_channel = metrics.Metric(
    name="channel",
    title=Title("Channel"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

graph_cisco_meraki_wireless_device_status_signal_power = graphs.Graph(
    name='cisco_meraki_wireless_device_status_signal_power',
    title=Title('Signal power'),
    compound_lines=['signal_power'],
    minimal_range=graphs.MinimalRange(0, 'signal_power:max'),
)

graph_cisco_meraki_wireless_device_status_channel_width = graphs.Graph(
    name='cisco_meraki_wireless_device_status_channel_width',
    title=Title('Channel Width'),
    compound_lines=['channel_width'],
    minimal_range=graphs.MinimalRange(0, 'channel_width:max'),
)

graph_cisco_meraki_wireless_device_status_channel = graphs.Graph(
    name='cisco_meraki_wireless_device_status_channel',
    title=Title('Channel'),
    compound_lines=['channel'],
    minimal_range=graphs.MinimalRange(0, 'channel:max'),
)

perfometer_signal_power = perfometers.Perfometer(
    name='signal_power',
    segments=['signal_power'],
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(40))
)

#
# API return Codes
#
metric_api_code_2xx = metrics.Metric(
    name="api_code_2xx",
    title=Title("Code 2xx"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GREEN,
)

metric_api_code_3xx = metrics.Metric(
    name="api_code_3xx",
    title=Title("Code 3xx"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_api_code_4xx = metrics.Metric(
    name="api_code_4xx",
    title=Title("Code 4xx"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_RED,
)

metric_api_code_5xx = metrics.Metric(
    name="api_code_5xx",
    title=Title("Code 5xx"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_RED,
)

graph_cisco_meraki_cisco_meraki_organisations_api_code = graphs.Bidirectional(
    name='cisco_meraki_cisco_meraki_organisations_api_code',
    title=Title('Cisco Meraki API response codes'),
    upper=graphs.Graph(
        name='api_code_ok',
        title=Title('Cisco Meraki API response codes'),
        simple_lines=[
            'api_code_2xx',
            'api_code_3xx',
        ],
        optional=[
            'api_code_2xx',
            'api_code_3xx',
        ]
    ),
    lower=graphs.Graph(
        name='api_codebad',
        title=Title('Cisco Meraki API response codes'),
        simple_lines=[
            'api_code_4xx',
            'api_code_5xx',
        ],
        optional=[
            'api_code_4xx',
            'api_code_5xx',
        ]
    ),
)

perfometer_api_code = perfometers.Stacked(
    name='api_code',
    lower=perfometers.Perfometer(
        name='api_code_2xx',
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(30)),
        segments=["api_code_2xx"],
    ),
    upper=perfometers.Perfometer(
        name='api_code_4xx',
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(30)),
        segments=["api_code_4xx"],
    )
)

perfometer_api_code_2xx = perfometers.Perfometer(
    name='api_code_2xx',
    segments=["api_code_2xx"],
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(50)),
)

perfometer_api_code_4xx = perfometers.Perfometer(
    name='api_code_4xx',
    segments=['api_code_4xx'],
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(50)),
)

#
# appliance performance/utilization
#
metric_utilization = metrics.Metric(
    name="utilization",
    title=Title("Utilization"),
    unit=UNIT_PERCENT,
    color=metrics.Color.LIGHT_GREEN,
)

graph_cisco_meraki_cisco_meraki_appliance_utilization = graphs.Graph(
    name='cisco_meraki_cisco_meraki_appliance_utilization',
    title=Title('Cisco Meraki Appliance Utilization'),
    compound_lines=['utilization'],
    simple_lines=[
        metrics.WarningOf("utilization"),
        metrics.CriticalOf("utilization"),
    ],
    minimal_range=graphs.MinimalRange(0, 100),
)

perfometer_utilization = perfometers.Perfometer(
    name='utilization',
    segments=['utilization'],
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
)
