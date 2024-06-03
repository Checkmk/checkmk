#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_hop_10_pl = metrics.Metric(
    name="hop_10_pl",
    title=Title("Hop 10 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_10_response_time = metrics.Metric(
    name="hop_10_response_time",
    title=Title("Hop 10 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_10_rta = metrics.Metric(
    name="hop_10_rta",
    title=Title("Hop 10 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_10_rtmax = metrics.Metric(
    name="hop_10_rtmax",
    title=Title("Hop 10 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_10_rtmin = metrics.Metric(
    name="hop_10_rtmin",
    title=Title("Hop 10 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_10_rtstddev = metrics.Metric(
    name="hop_10_rtstddev",
    title=Title("Hop 10 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_11_pl = metrics.Metric(
    name="hop_11_pl",
    title=Title("Hop 11 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_11_response_time = metrics.Metric(
    name="hop_11_response_time",
    title=Title("Hop 11 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_11_rta = metrics.Metric(
    name="hop_11_rta",
    title=Title("Hop 11 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_11_rtmax = metrics.Metric(
    name="hop_11_rtmax",
    title=Title("Hop 11 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_11_rtmin = metrics.Metric(
    name="hop_11_rtmin",
    title=Title("Hop 11 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_11_rtstddev = metrics.Metric(
    name="hop_11_rtstddev",
    title=Title("Hop 11 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_12_pl = metrics.Metric(
    name="hop_12_pl",
    title=Title("Hop 12 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_12_response_time = metrics.Metric(
    name="hop_12_response_time",
    title=Title("Hop 12 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_12_rta = metrics.Metric(
    name="hop_12_rta",
    title=Title("Hop 12 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_12_rtmax = metrics.Metric(
    name="hop_12_rtmax",
    title=Title("Hop 12 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_12_rtmin = metrics.Metric(
    name="hop_12_rtmin",
    title=Title("Hop 12 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_12_rtstddev = metrics.Metric(
    name="hop_12_rtstddev",
    title=Title("Hop 12 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_13_pl = metrics.Metric(
    name="hop_13_pl",
    title=Title("Hop 13 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_13_response_time = metrics.Metric(
    name="hop_13_response_time",
    title=Title("Hop 13 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_13_rta = metrics.Metric(
    name="hop_13_rta",
    title=Title("Hop 13 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_13_rtmax = metrics.Metric(
    name="hop_13_rtmax",
    title=Title("Hop 13 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_13_rtmin = metrics.Metric(
    name="hop_13_rtmin",
    title=Title("Hop 13 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_13_rtstddev = metrics.Metric(
    name="hop_13_rtstddev",
    title=Title("Hop 13 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_14_pl = metrics.Metric(
    name="hop_14_pl",
    title=Title("Hop 14 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_14_response_time = metrics.Metric(
    name="hop_14_response_time",
    title=Title("Hop 14 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_14_rta = metrics.Metric(
    name="hop_14_rta",
    title=Title("Hop 14 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_14_rtmax = metrics.Metric(
    name="hop_14_rtmax",
    title=Title("Hop 14 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_14_rtmin = metrics.Metric(
    name="hop_14_rtmin",
    title=Title("Hop 14 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_14_rtstddev = metrics.Metric(
    name="hop_14_rtstddev",
    title=Title("Hop 14 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_15_pl = metrics.Metric(
    name="hop_15_pl",
    title=Title("Hop 15 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_15_response_time = metrics.Metric(
    name="hop_15_response_time",
    title=Title("Hop 15 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_15_rta = metrics.Metric(
    name="hop_15_rta",
    title=Title("Hop 15 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_15_rtmax = metrics.Metric(
    name="hop_15_rtmax",
    title=Title("Hop 15 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_15_rtmin = metrics.Metric(
    name="hop_15_rtmin",
    title=Title("Hop 15 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_15_rtstddev = metrics.Metric(
    name="hop_15_rtstddev",
    title=Title("Hop 15 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_16_pl = metrics.Metric(
    name="hop_16_pl",
    title=Title("Hop 16 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_16_response_time = metrics.Metric(
    name="hop_16_response_time",
    title=Title("Hop 16 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_16_rta = metrics.Metric(
    name="hop_16_rta",
    title=Title("Hop 16 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_16_rtmax = metrics.Metric(
    name="hop_16_rtmax",
    title=Title("Hop 16 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_16_rtmin = metrics.Metric(
    name="hop_16_rtmin",
    title=Title("Hop 16 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_16_rtstddev = metrics.Metric(
    name="hop_16_rtstddev",
    title=Title("Hop 16 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_17_pl = metrics.Metric(
    name="hop_17_pl",
    title=Title("Hop 17 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_17_response_time = metrics.Metric(
    name="hop_17_response_time",
    title=Title("Hop 17 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_17_rta = metrics.Metric(
    name="hop_17_rta",
    title=Title("Hop 17 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_17_rtmax = metrics.Metric(
    name="hop_17_rtmax",
    title=Title("Hop 17 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_17_rtmin = metrics.Metric(
    name="hop_17_rtmin",
    title=Title("Hop 17 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_17_rtstddev = metrics.Metric(
    name="hop_17_rtstddev",
    title=Title("Hop 17 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_18_pl = metrics.Metric(
    name="hop_18_pl",
    title=Title("Hop 18 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_18_response_time = metrics.Metric(
    name="hop_18_response_time",
    title=Title("Hop 18 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_18_rta = metrics.Metric(
    name="hop_18_rta",
    title=Title("Hop 18 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_18_rtmax = metrics.Metric(
    name="hop_18_rtmax",
    title=Title("Hop 18 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_18_rtmin = metrics.Metric(
    name="hop_18_rtmin",
    title=Title("Hop 18 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_18_rtstddev = metrics.Metric(
    name="hop_18_rtstddev",
    title=Title("Hop 18 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_19_pl = metrics.Metric(
    name="hop_19_pl",
    title=Title("Hop 19 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_19_response_time = metrics.Metric(
    name="hop_19_response_time",
    title=Title("Hop 19 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_19_rta = metrics.Metric(
    name="hop_19_rta",
    title=Title("Hop 19 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_19_rtmax = metrics.Metric(
    name="hop_19_rtmax",
    title=Title("Hop 19 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_19_rtmin = metrics.Metric(
    name="hop_19_rtmin",
    title=Title("Hop 19 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_19_rtstddev = metrics.Metric(
    name="hop_19_rtstddev",
    title=Title("Hop 19 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_1_pl = metrics.Metric(
    name="hop_1_pl",
    title=Title("Hop 1 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_1_response_time = metrics.Metric(
    name="hop_1_response_time",
    title=Title("Hop 1 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_1_rta = metrics.Metric(
    name="hop_1_rta",
    title=Title("Hop 1 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_1_rtmax = metrics.Metric(
    name="hop_1_rtmax",
    title=Title("Hop 1 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_1_rtmin = metrics.Metric(
    name="hop_1_rtmin",
    title=Title("Hop 1 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_1_rtstddev = metrics.Metric(
    name="hop_1_rtstddev",
    title=Title("Hop 1 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_20_pl = metrics.Metric(
    name="hop_20_pl",
    title=Title("Hop 20 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_20_response_time = metrics.Metric(
    name="hop_20_response_time",
    title=Title("Hop 20 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_20_rta = metrics.Metric(
    name="hop_20_rta",
    title=Title("Hop 20 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_20_rtmax = metrics.Metric(
    name="hop_20_rtmax",
    title=Title("Hop 20 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_20_rtmin = metrics.Metric(
    name="hop_20_rtmin",
    title=Title("Hop 20 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_20_rtstddev = metrics.Metric(
    name="hop_20_rtstddev",
    title=Title("Hop 20 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_21_pl = metrics.Metric(
    name="hop_21_pl",
    title=Title("Hop 21 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_21_response_time = metrics.Metric(
    name="hop_21_response_time",
    title=Title("Hop 21 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_21_rta = metrics.Metric(
    name="hop_21_rta",
    title=Title("Hop 21 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_21_rtmax = metrics.Metric(
    name="hop_21_rtmax",
    title=Title("Hop 21 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_21_rtmin = metrics.Metric(
    name="hop_21_rtmin",
    title=Title("Hop 21 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_21_rtstddev = metrics.Metric(
    name="hop_21_rtstddev",
    title=Title("Hop 21 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_22_pl = metrics.Metric(
    name="hop_22_pl",
    title=Title("Hop 22 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_22_response_time = metrics.Metric(
    name="hop_22_response_time",
    title=Title("Hop 22 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_22_rta = metrics.Metric(
    name="hop_22_rta",
    title=Title("Hop 22 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_22_rtmax = metrics.Metric(
    name="hop_22_rtmax",
    title=Title("Hop 22 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_22_rtmin = metrics.Metric(
    name="hop_22_rtmin",
    title=Title("Hop 22 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_22_rtstddev = metrics.Metric(
    name="hop_22_rtstddev",
    title=Title("Hop 22 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_23_pl = metrics.Metric(
    name="hop_23_pl",
    title=Title("Hop 23 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_23_response_time = metrics.Metric(
    name="hop_23_response_time",
    title=Title("Hop 23 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_23_rta = metrics.Metric(
    name="hop_23_rta",
    title=Title("Hop 23 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_23_rtmax = metrics.Metric(
    name="hop_23_rtmax",
    title=Title("Hop 23 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_23_rtmin = metrics.Metric(
    name="hop_23_rtmin",
    title=Title("Hop 23 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_23_rtstddev = metrics.Metric(
    name="hop_23_rtstddev",
    title=Title("Hop 23 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_24_pl = metrics.Metric(
    name="hop_24_pl",
    title=Title("Hop 24 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_24_response_time = metrics.Metric(
    name="hop_24_response_time",
    title=Title("Hop 24 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_24_rta = metrics.Metric(
    name="hop_24_rta",
    title=Title("Hop 24 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_24_rtmax = metrics.Metric(
    name="hop_24_rtmax",
    title=Title("Hop 24 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_24_rtmin = metrics.Metric(
    name="hop_24_rtmin",
    title=Title("Hop 24 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_24_rtstddev = metrics.Metric(
    name="hop_24_rtstddev",
    title=Title("Hop 24 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_25_pl = metrics.Metric(
    name="hop_25_pl",
    title=Title("Hop 25 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_25_response_time = metrics.Metric(
    name="hop_25_response_time",
    title=Title("Hop 25 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_25_rta = metrics.Metric(
    name="hop_25_rta",
    title=Title("Hop 25 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_25_rtmax = metrics.Metric(
    name="hop_25_rtmax",
    title=Title("Hop 25 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_25_rtmin = metrics.Metric(
    name="hop_25_rtmin",
    title=Title("Hop 25 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_25_rtstddev = metrics.Metric(
    name="hop_25_rtstddev",
    title=Title("Hop 25 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_26_pl = metrics.Metric(
    name="hop_26_pl",
    title=Title("Hop 26 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_26_response_time = metrics.Metric(
    name="hop_26_response_time",
    title=Title("Hop 26 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_26_rta = metrics.Metric(
    name="hop_26_rta",
    title=Title("Hop 26 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_26_rtmax = metrics.Metric(
    name="hop_26_rtmax",
    title=Title("Hop 26 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_26_rtmin = metrics.Metric(
    name="hop_26_rtmin",
    title=Title("Hop 26 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_26_rtstddev = metrics.Metric(
    name="hop_26_rtstddev",
    title=Title("Hop 26 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_27_pl = metrics.Metric(
    name="hop_27_pl",
    title=Title("Hop 27 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_27_response_time = metrics.Metric(
    name="hop_27_response_time",
    title=Title("Hop 27 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_27_rta = metrics.Metric(
    name="hop_27_rta",
    title=Title("Hop 27 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_27_rtmax = metrics.Metric(
    name="hop_27_rtmax",
    title=Title("Hop 27 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_27_rtmin = metrics.Metric(
    name="hop_27_rtmin",
    title=Title("Hop 27 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_27_rtstddev = metrics.Metric(
    name="hop_27_rtstddev",
    title=Title("Hop 27 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_28_pl = metrics.Metric(
    name="hop_28_pl",
    title=Title("Hop 28 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_28_response_time = metrics.Metric(
    name="hop_28_response_time",
    title=Title("Hop 28 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_28_rta = metrics.Metric(
    name="hop_28_rta",
    title=Title("Hop 28 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_28_rtmax = metrics.Metric(
    name="hop_28_rtmax",
    title=Title("Hop 28 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_28_rtmin = metrics.Metric(
    name="hop_28_rtmin",
    title=Title("Hop 28 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_28_rtstddev = metrics.Metric(
    name="hop_28_rtstddev",
    title=Title("Hop 28 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_29_pl = metrics.Metric(
    name="hop_29_pl",
    title=Title("Hop 29 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_29_response_time = metrics.Metric(
    name="hop_29_response_time",
    title=Title("Hop 29 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_29_rta = metrics.Metric(
    name="hop_29_rta",
    title=Title("Hop 29 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_29_rtmax = metrics.Metric(
    name="hop_29_rtmax",
    title=Title("Hop 29 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_29_rtmin = metrics.Metric(
    name="hop_29_rtmin",
    title=Title("Hop 29 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_29_rtstddev = metrics.Metric(
    name="hop_29_rtstddev",
    title=Title("Hop 29 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_2_pl = metrics.Metric(
    name="hop_2_pl",
    title=Title("Hop 2 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_2_response_time = metrics.Metric(
    name="hop_2_response_time",
    title=Title("Hop 2 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_2_rta = metrics.Metric(
    name="hop_2_rta",
    title=Title("Hop 2 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_2_rtmax = metrics.Metric(
    name="hop_2_rtmax",
    title=Title("Hop 2 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_2_rtmin = metrics.Metric(
    name="hop_2_rtmin",
    title=Title("Hop 2 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_2_rtstddev = metrics.Metric(
    name="hop_2_rtstddev",
    title=Title("Hop 2 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_30_pl = metrics.Metric(
    name="hop_30_pl",
    title=Title("Hop 30 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_30_response_time = metrics.Metric(
    name="hop_30_response_time",
    title=Title("Hop 30 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_30_rta = metrics.Metric(
    name="hop_30_rta",
    title=Title("Hop 30 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_30_rtmax = metrics.Metric(
    name="hop_30_rtmax",
    title=Title("Hop 30 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_30_rtmin = metrics.Metric(
    name="hop_30_rtmin",
    title=Title("Hop 30 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_30_rtstddev = metrics.Metric(
    name="hop_30_rtstddev",
    title=Title("Hop 30 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_31_pl = metrics.Metric(
    name="hop_31_pl",
    title=Title("Hop 31 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_31_response_time = metrics.Metric(
    name="hop_31_response_time",
    title=Title("Hop 31 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_31_rta = metrics.Metric(
    name="hop_31_rta",
    title=Title("Hop 31 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_31_rtmax = metrics.Metric(
    name="hop_31_rtmax",
    title=Title("Hop 31 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_31_rtmin = metrics.Metric(
    name="hop_31_rtmin",
    title=Title("Hop 31 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_31_rtstddev = metrics.Metric(
    name="hop_31_rtstddev",
    title=Title("Hop 31 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_32_pl = metrics.Metric(
    name="hop_32_pl",
    title=Title("Hop 32 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_32_response_time = metrics.Metric(
    name="hop_32_response_time",
    title=Title("Hop 32 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_32_rta = metrics.Metric(
    name="hop_32_rta",
    title=Title("Hop 32 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_32_rtmax = metrics.Metric(
    name="hop_32_rtmax",
    title=Title("Hop 32 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_32_rtmin = metrics.Metric(
    name="hop_32_rtmin",
    title=Title("Hop 32 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_32_rtstddev = metrics.Metric(
    name="hop_32_rtstddev",
    title=Title("Hop 32 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_33_pl = metrics.Metric(
    name="hop_33_pl",
    title=Title("Hop 33 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_33_response_time = metrics.Metric(
    name="hop_33_response_time",
    title=Title("Hop 33 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_33_rta = metrics.Metric(
    name="hop_33_rta",
    title=Title("Hop 33 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_33_rtmax = metrics.Metric(
    name="hop_33_rtmax",
    title=Title("Hop 33 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_33_rtmin = metrics.Metric(
    name="hop_33_rtmin",
    title=Title("Hop 33 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_33_rtstddev = metrics.Metric(
    name="hop_33_rtstddev",
    title=Title("Hop 33 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_34_pl = metrics.Metric(
    name="hop_34_pl",
    title=Title("Hop 34 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_34_response_time = metrics.Metric(
    name="hop_34_response_time",
    title=Title("Hop 34 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_34_rta = metrics.Metric(
    name="hop_34_rta",
    title=Title("Hop 34 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_34_rtmax = metrics.Metric(
    name="hop_34_rtmax",
    title=Title("Hop 34 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_34_rtmin = metrics.Metric(
    name="hop_34_rtmin",
    title=Title("Hop 34 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_34_rtstddev = metrics.Metric(
    name="hop_34_rtstddev",
    title=Title("Hop 34 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_35_pl = metrics.Metric(
    name="hop_35_pl",
    title=Title("Hop 35 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_35_response_time = metrics.Metric(
    name="hop_35_response_time",
    title=Title("Hop 35 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_35_rta = metrics.Metric(
    name="hop_35_rta",
    title=Title("Hop 35 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_35_rtmax = metrics.Metric(
    name="hop_35_rtmax",
    title=Title("Hop 35 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_35_rtmin = metrics.Metric(
    name="hop_35_rtmin",
    title=Title("Hop 35 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_35_rtstddev = metrics.Metric(
    name="hop_35_rtstddev",
    title=Title("Hop 35 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_36_pl = metrics.Metric(
    name="hop_36_pl",
    title=Title("Hop 36 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_36_response_time = metrics.Metric(
    name="hop_36_response_time",
    title=Title("Hop 36 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_36_rta = metrics.Metric(
    name="hop_36_rta",
    title=Title("Hop 36 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_36_rtmax = metrics.Metric(
    name="hop_36_rtmax",
    title=Title("Hop 36 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_36_rtmin = metrics.Metric(
    name="hop_36_rtmin",
    title=Title("Hop 36 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_36_rtstddev = metrics.Metric(
    name="hop_36_rtstddev",
    title=Title("Hop 36 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_37_pl = metrics.Metric(
    name="hop_37_pl",
    title=Title("Hop 37 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_37_response_time = metrics.Metric(
    name="hop_37_response_time",
    title=Title("Hop 37 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_37_rta = metrics.Metric(
    name="hop_37_rta",
    title=Title("Hop 37 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_37_rtmax = metrics.Metric(
    name="hop_37_rtmax",
    title=Title("Hop 37 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_37_rtmin = metrics.Metric(
    name="hop_37_rtmin",
    title=Title("Hop 37 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_37_rtstddev = metrics.Metric(
    name="hop_37_rtstddev",
    title=Title("Hop 37 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_38_pl = metrics.Metric(
    name="hop_38_pl",
    title=Title("Hop 38 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_38_response_time = metrics.Metric(
    name="hop_38_response_time",
    title=Title("Hop 38 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_38_rta = metrics.Metric(
    name="hop_38_rta",
    title=Title("Hop 38 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_38_rtmax = metrics.Metric(
    name="hop_38_rtmax",
    title=Title("Hop 38 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_38_rtmin = metrics.Metric(
    name="hop_38_rtmin",
    title=Title("Hop 38 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_38_rtstddev = metrics.Metric(
    name="hop_38_rtstddev",
    title=Title("Hop 38 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_39_pl = metrics.Metric(
    name="hop_39_pl",
    title=Title("Hop 39 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_39_response_time = metrics.Metric(
    name="hop_39_response_time",
    title=Title("Hop 39 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_39_rta = metrics.Metric(
    name="hop_39_rta",
    title=Title("Hop 39 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_39_rtmax = metrics.Metric(
    name="hop_39_rtmax",
    title=Title("Hop 39 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_39_rtmin = metrics.Metric(
    name="hop_39_rtmin",
    title=Title("Hop 39 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_39_rtstddev = metrics.Metric(
    name="hop_39_rtstddev",
    title=Title("Hop 39 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_3_pl = metrics.Metric(
    name="hop_3_pl",
    title=Title("Hop 3 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_3_response_time = metrics.Metric(
    name="hop_3_response_time",
    title=Title("Hop 3 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_3_rta = metrics.Metric(
    name="hop_3_rta",
    title=Title("Hop 3 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_3_rtmax = metrics.Metric(
    name="hop_3_rtmax",
    title=Title("Hop 3 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_3_rtmin = metrics.Metric(
    name="hop_3_rtmin",
    title=Title("Hop 3 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_3_rtstddev = metrics.Metric(
    name="hop_3_rtstddev",
    title=Title("Hop 3 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_40_pl = metrics.Metric(
    name="hop_40_pl",
    title=Title("Hop 40 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_40_response_time = metrics.Metric(
    name="hop_40_response_time",
    title=Title("Hop 40 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_40_rta = metrics.Metric(
    name="hop_40_rta",
    title=Title("Hop 40 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_40_rtmax = metrics.Metric(
    name="hop_40_rtmax",
    title=Title("Hop 40 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_40_rtmin = metrics.Metric(
    name="hop_40_rtmin",
    title=Title("Hop 40 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_40_rtstddev = metrics.Metric(
    name="hop_40_rtstddev",
    title=Title("Hop 40 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_41_pl = metrics.Metric(
    name="hop_41_pl",
    title=Title("Hop 41 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_41_response_time = metrics.Metric(
    name="hop_41_response_time",
    title=Title("Hop 41 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_41_rta = metrics.Metric(
    name="hop_41_rta",
    title=Title("Hop 41 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_41_rtmax = metrics.Metric(
    name="hop_41_rtmax",
    title=Title("Hop 41 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_41_rtmin = metrics.Metric(
    name="hop_41_rtmin",
    title=Title("Hop 41 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_41_rtstddev = metrics.Metric(
    name="hop_41_rtstddev",
    title=Title("Hop 41 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_42_pl = metrics.Metric(
    name="hop_42_pl",
    title=Title("Hop 42 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_42_response_time = metrics.Metric(
    name="hop_42_response_time",
    title=Title("Hop 42 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_42_rta = metrics.Metric(
    name="hop_42_rta",
    title=Title("Hop 42 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_42_rtmax = metrics.Metric(
    name="hop_42_rtmax",
    title=Title("Hop 42 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_42_rtmin = metrics.Metric(
    name="hop_42_rtmin",
    title=Title("Hop 42 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_42_rtstddev = metrics.Metric(
    name="hop_42_rtstddev",
    title=Title("Hop 42 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_43_pl = metrics.Metric(
    name="hop_43_pl",
    title=Title("Hop 43 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_43_response_time = metrics.Metric(
    name="hop_43_response_time",
    title=Title("Hop 43 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_43_rta = metrics.Metric(
    name="hop_43_rta",
    title=Title("Hop 43 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_43_rtmax = metrics.Metric(
    name="hop_43_rtmax",
    title=Title("Hop 43 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_43_rtmin = metrics.Metric(
    name="hop_43_rtmin",
    title=Title("Hop 43 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_43_rtstddev = metrics.Metric(
    name="hop_43_rtstddev",
    title=Title("Hop 43 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_44_pl = metrics.Metric(
    name="hop_44_pl",
    title=Title("Hop 44 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_44_response_time = metrics.Metric(
    name="hop_44_response_time",
    title=Title("Hop 44 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_44_rta = metrics.Metric(
    name="hop_44_rta",
    title=Title("Hop 44 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_44_rtmax = metrics.Metric(
    name="hop_44_rtmax",
    title=Title("Hop 44 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_44_rtmin = metrics.Metric(
    name="hop_44_rtmin",
    title=Title("Hop 44 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_44_rtstddev = metrics.Metric(
    name="hop_44_rtstddev",
    title=Title("Hop 44 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_4_pl = metrics.Metric(
    name="hop_4_pl",
    title=Title("Hop 4 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_4_response_time = metrics.Metric(
    name="hop_4_response_time",
    title=Title("Hop 4 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_4_rta = metrics.Metric(
    name="hop_4_rta",
    title=Title("Hop 4 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_4_rtmax = metrics.Metric(
    name="hop_4_rtmax",
    title=Title("Hop 4 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_4_rtmin = metrics.Metric(
    name="hop_4_rtmin",
    title=Title("Hop 4 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_4_rtstddev = metrics.Metric(
    name="hop_4_rtstddev",
    title=Title("Hop 4 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_5_pl = metrics.Metric(
    name="hop_5_pl",
    title=Title("Hop 5 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_5_response_time = metrics.Metric(
    name="hop_5_response_time",
    title=Title("Hop 5 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_5_rta = metrics.Metric(
    name="hop_5_rta",
    title=Title("Hop 5 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_5_rtmax = metrics.Metric(
    name="hop_5_rtmax",
    title=Title("Hop 5 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_5_rtmin = metrics.Metric(
    name="hop_5_rtmin",
    title=Title("Hop 5 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_5_rtstddev = metrics.Metric(
    name="hop_5_rtstddev",
    title=Title("Hop 5 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_6_pl = metrics.Metric(
    name="hop_6_pl",
    title=Title("Hop 6 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_6_response_time = metrics.Metric(
    name="hop_6_response_time",
    title=Title("Hop 6 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_6_rta = metrics.Metric(
    name="hop_6_rta",
    title=Title("Hop 6 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_6_rtmax = metrics.Metric(
    name="hop_6_rtmax",
    title=Title("Hop 6 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_6_rtmin = metrics.Metric(
    name="hop_6_rtmin",
    title=Title("Hop 6 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_6_rtstddev = metrics.Metric(
    name="hop_6_rtstddev",
    title=Title("Hop 6 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_7_pl = metrics.Metric(
    name="hop_7_pl",
    title=Title("Hop 7 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_7_response_time = metrics.Metric(
    name="hop_7_response_time",
    title=Title("Hop 7 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_7_rta = metrics.Metric(
    name="hop_7_rta",
    title=Title("Hop 7 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_7_rtmax = metrics.Metric(
    name="hop_7_rtmax",
    title=Title("Hop 7 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_7_rtmin = metrics.Metric(
    name="hop_7_rtmin",
    title=Title("Hop 7 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_7_rtstddev = metrics.Metric(
    name="hop_7_rtstddev",
    title=Title("Hop 7 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_8_pl = metrics.Metric(
    name="hop_8_pl",
    title=Title("Hop 8 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_8_response_time = metrics.Metric(
    name="hop_8_response_time",
    title=Title("Hop 8 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_8_rta = metrics.Metric(
    name="hop_8_rta",
    title=Title("Hop 8 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_8_rtmax = metrics.Metric(
    name="hop_8_rtmax",
    title=Title("Hop 8 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_8_rtmin = metrics.Metric(
    name="hop_8_rtmin",
    title=Title("Hop 8 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_8_rtstddev = metrics.Metric(
    name="hop_8_rtstddev",
    title=Title("Hop 8 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)
metric_hop_9_pl = metrics.Metric(
    name="hop_9_pl",
    title=Title("Hop 9 packet loss"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_hop_9_response_time = metrics.Metric(
    name="hop_9_response_time",
    title=Title("Hop 9 response time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_hop_9_rta = metrics.Metric(
    name="hop_9_rta",
    title=Title("Hop 9 round trip average"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_hop_9_rtmax = metrics.Metric(
    name="hop_9_rtmax",
    title=Title("Hop 9 round trip maximum"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_hop_9_rtmin = metrics.Metric(
    name="hop_9_rtmin",
    title=Title("Hop 9 round trip minimum"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_hop_9_rtstddev = metrics.Metric(
    name="hop_9_rtstddev",
    title=Title("Hop 9 round trip standard devation"),
    unit=UNIT_TIME,
    color=metrics.Color.PINK,
)

graph_hop_10_packet_loss = graphs.Graph(
    name="hop_10_packet_loss",
    title=Title("Hop 10 packet loss"),
    compound_lines=["hop_10_pl"],
)
graph_hop_10_round_trip_average = graphs.Graph(
    name="hop_10_round_trip_average",
    title=Title("Hop 10 round trip average"),
    simple_lines=[
        "hop_10_rtmax",
        "hop_10_rtmin",
        "hop_10_rta",
        "hop_10_rtstddev",
    ],
)
graph_hop_11_packet_loss = graphs.Graph(
    name="hop_11_packet_loss",
    title=Title("Hop 11 packet loss"),
    compound_lines=["hop_11_pl"],
)
graph_hop_11_round_trip_average = graphs.Graph(
    name="hop_11_round_trip_average",
    title=Title("Hop 11 round trip average"),
    simple_lines=[
        "hop_11_rtmax",
        "hop_11_rtmin",
        "hop_11_rta",
        "hop_11_rtstddev",
    ],
)
graph_hop_12_packet_loss = graphs.Graph(
    name="hop_12_packet_loss",
    title=Title("Hop 12 packet loss"),
    compound_lines=["hop_12_pl"],
)
graph_hop_12_round_trip_average = graphs.Graph(
    name="hop_12_round_trip_average",
    title=Title("Hop 12 round trip average"),
    simple_lines=[
        "hop_12_rtmax",
        "hop_12_rtmin",
        "hop_12_rta",
        "hop_12_rtstddev",
    ],
)
graph_hop_13_packet_loss = graphs.Graph(
    name="hop_13_packet_loss",
    title=Title("Hop 13 packet loss"),
    compound_lines=["hop_13_pl"],
)
graph_hop_13_round_trip_average = graphs.Graph(
    name="hop_13_round_trip_average",
    title=Title("Hop 13 round trip average"),
    simple_lines=[
        "hop_13_rtmax",
        "hop_13_rtmin",
        "hop_13_rta",
        "hop_13_rtstddev",
    ],
)
graph_hop_14_packet_loss = graphs.Graph(
    name="hop_14_packet_loss",
    title=Title("Hop 14 packet loss"),
    compound_lines=["hop_14_pl"],
)
graph_hop_14_round_trip_average = graphs.Graph(
    name="hop_14_round_trip_average",
    title=Title("Hop 14 round trip average"),
    simple_lines=[
        "hop_14_rtmax",
        "hop_14_rtmin",
        "hop_14_rta",
        "hop_14_rtstddev",
    ],
)
graph_hop_15_packet_loss = graphs.Graph(
    name="hop_15_packet_loss",
    title=Title("Hop 15 packet loss"),
    compound_lines=["hop_15_pl"],
)
graph_hop_15_round_trip_average = graphs.Graph(
    name="hop_15_round_trip_average",
    title=Title("Hop 15 round trip average"),
    simple_lines=[
        "hop_15_rtmax",
        "hop_15_rtmin",
        "hop_15_rta",
        "hop_15_rtstddev",
    ],
)
graph_hop_16_packet_loss = graphs.Graph(
    name="hop_16_packet_loss",
    title=Title("Hop 16 packet loss"),
    compound_lines=["hop_16_pl"],
)
graph_hop_16_round_trip_average = graphs.Graph(
    name="hop_16_round_trip_average",
    title=Title("Hop 16 round trip average"),
    simple_lines=[
        "hop_16_rtmax",
        "hop_16_rtmin",
        "hop_16_rta",
        "hop_16_rtstddev",
    ],
)
graph_hop_17_packet_loss = graphs.Graph(
    name="hop_17_packet_loss",
    title=Title("Hop 17 packet loss"),
    compound_lines=["hop_17_pl"],
)
graph_hop_17_round_trip_average = graphs.Graph(
    name="hop_17_round_trip_average",
    title=Title("Hop 17 round trip average"),
    simple_lines=[
        "hop_17_rtmax",
        "hop_17_rtmin",
        "hop_17_rta",
        "hop_17_rtstddev",
    ],
)
graph_hop_18_packet_loss = graphs.Graph(
    name="hop_18_packet_loss",
    title=Title("Hop 18 packet loss"),
    compound_lines=["hop_18_pl"],
)
graph_hop_18_round_trip_average = graphs.Graph(
    name="hop_18_round_trip_average",
    title=Title("Hop 18 round trip average"),
    simple_lines=[
        "hop_18_rtmax",
        "hop_18_rtmin",
        "hop_18_rta",
        "hop_18_rtstddev",
    ],
)
graph_hop_19_packet_loss = graphs.Graph(
    name="hop_19_packet_loss",
    title=Title("Hop 19 packet loss"),
    compound_lines=["hop_19_pl"],
)
graph_hop_19_round_trip_average = graphs.Graph(
    name="hop_19_round_trip_average",
    title=Title("Hop 19 round trip average"),
    simple_lines=[
        "hop_19_rtmax",
        "hop_19_rtmin",
        "hop_19_rta",
        "hop_19_rtstddev",
    ],
)
graph_hop_1_packet_loss = graphs.Graph(
    name="hop_1_packet_loss",
    title=Title("Hop 1 packet loss"),
    compound_lines=["hop_1_pl"],
)
graph_hop_1_round_trip_average = graphs.Graph(
    name="hop_1_round_trip_average",
    title=Title("Hop 1 round trip average"),
    simple_lines=[
        "hop_1_rtmax",
        "hop_1_rtmin",
        "hop_1_rta",
        "hop_1_rtstddev",
    ],
)
graph_hop_20_packet_loss = graphs.Graph(
    name="hop_20_packet_loss",
    title=Title("Hop 20 packet loss"),
    compound_lines=["hop_20_pl"],
)
graph_hop_20_round_trip_average = graphs.Graph(
    name="hop_20_round_trip_average",
    title=Title("Hop 20 round trip average"),
    simple_lines=[
        "hop_20_rtmax",
        "hop_20_rtmin",
        "hop_20_rta",
        "hop_20_rtstddev",
    ],
)
graph_hop_21_packet_loss = graphs.Graph(
    name="hop_21_packet_loss",
    title=Title("Hop 21 packet loss"),
    compound_lines=["hop_21_pl"],
)
graph_hop_21_round_trip_average = graphs.Graph(
    name="hop_21_round_trip_average",
    title=Title("Hop 21 round trip average"),
    simple_lines=[
        "hop_21_rtmax",
        "hop_21_rtmin",
        "hop_21_rta",
        "hop_21_rtstddev",
    ],
)
graph_hop_22_packet_loss = graphs.Graph(
    name="hop_22_packet_loss",
    title=Title("Hop 22 packet loss"),
    compound_lines=["hop_22_pl"],
)
graph_hop_22_round_trip_average = graphs.Graph(
    name="hop_22_round_trip_average",
    title=Title("Hop 22 round trip average"),
    simple_lines=[
        "hop_22_rtmax",
        "hop_22_rtmin",
        "hop_22_rta",
        "hop_22_rtstddev",
    ],
)
graph_hop_23_packet_loss = graphs.Graph(
    name="hop_23_packet_loss",
    title=Title("Hop 23 packet loss"),
    compound_lines=["hop_23_pl"],
)
graph_hop_23_round_trip_average = graphs.Graph(
    name="hop_23_round_trip_average",
    title=Title("Hop 23 round trip average"),
    simple_lines=[
        "hop_23_rtmax",
        "hop_23_rtmin",
        "hop_23_rta",
        "hop_23_rtstddev",
    ],
)
graph_hop_24_packet_loss = graphs.Graph(
    name="hop_24_packet_loss",
    title=Title("Hop 24 packet loss"),
    compound_lines=["hop_24_pl"],
)
graph_hop_24_round_trip_average = graphs.Graph(
    name="hop_24_round_trip_average",
    title=Title("Hop 24 round trip average"),
    simple_lines=[
        "hop_24_rtmax",
        "hop_24_rtmin",
        "hop_24_rta",
        "hop_24_rtstddev",
    ],
)
graph_hop_25_packet_loss = graphs.Graph(
    name="hop_25_packet_loss",
    title=Title("Hop 25 packet loss"),
    compound_lines=["hop_25_pl"],
)
graph_hop_25_round_trip_average = graphs.Graph(
    name="hop_25_round_trip_average",
    title=Title("Hop 25 round trip average"),
    simple_lines=[
        "hop_25_rtmax",
        "hop_25_rtmin",
        "hop_25_rta",
        "hop_25_rtstddev",
    ],
)
graph_hop_26_packet_loss = graphs.Graph(
    name="hop_26_packet_loss",
    title=Title("Hop 26 packet loss"),
    compound_lines=["hop_26_pl"],
)
graph_hop_26_round_trip_average = graphs.Graph(
    name="hop_26_round_trip_average",
    title=Title("Hop 26 round trip average"),
    simple_lines=[
        "hop_26_rtmax",
        "hop_26_rtmin",
        "hop_26_rta",
        "hop_26_rtstddev",
    ],
)
graph_hop_27_packet_loss = graphs.Graph(
    name="hop_27_packet_loss",
    title=Title("Hop 27 packet loss"),
    compound_lines=["hop_27_pl"],
)
graph_hop_27_round_trip_average = graphs.Graph(
    name="hop_27_round_trip_average",
    title=Title("Hop 27 round trip average"),
    simple_lines=[
        "hop_27_rtmax",
        "hop_27_rtmin",
        "hop_27_rta",
        "hop_27_rtstddev",
    ],
)
graph_hop_28_packet_loss = graphs.Graph(
    name="hop_28_packet_loss",
    title=Title("Hop 28 packet loss"),
    compound_lines=["hop_28_pl"],
)
graph_hop_28_round_trip_average = graphs.Graph(
    name="hop_28_round_trip_average",
    title=Title("Hop 28 round trip average"),
    simple_lines=[
        "hop_28_rtmax",
        "hop_28_rtmin",
        "hop_28_rta",
        "hop_28_rtstddev",
    ],
)
graph_hop_29_packet_loss = graphs.Graph(
    name="hop_29_packet_loss",
    title=Title("Hop 29 packet loss"),
    compound_lines=["hop_29_pl"],
)
graph_hop_29_round_trip_average = graphs.Graph(
    name="hop_29_round_trip_average",
    title=Title("Hop 29 round trip average"),
    simple_lines=[
        "hop_29_rtmax",
        "hop_29_rtmin",
        "hop_29_rta",
        "hop_29_rtstddev",
    ],
)
graph_hop_2_packet_loss = graphs.Graph(
    name="hop_2_packet_loss",
    title=Title("Hop 2 packet loss"),
    compound_lines=["hop_2_pl"],
)
graph_hop_2_round_trip_average = graphs.Graph(
    name="hop_2_round_trip_average",
    title=Title("Hop 2 round trip average"),
    simple_lines=[
        "hop_2_rtmax",
        "hop_2_rtmin",
        "hop_2_rta",
        "hop_2_rtstddev",
    ],
)
graph_hop_30_packet_loss = graphs.Graph(
    name="hop_30_packet_loss",
    title=Title("Hop 30 packet loss"),
    compound_lines=["hop_30_pl"],
)
graph_hop_30_round_trip_average = graphs.Graph(
    name="hop_30_round_trip_average",
    title=Title("Hop 30 round trip average"),
    simple_lines=[
        "hop_30_rtmax",
        "hop_30_rtmin",
        "hop_30_rta",
        "hop_30_rtstddev",
    ],
)
graph_hop_31_packet_loss = graphs.Graph(
    name="hop_31_packet_loss",
    title=Title("Hop 31 packet loss"),
    compound_lines=["hop_31_pl"],
)
graph_hop_31_round_trip_average = graphs.Graph(
    name="hop_31_round_trip_average",
    title=Title("Hop 31 round trip average"),
    simple_lines=[
        "hop_31_rtmax",
        "hop_31_rtmin",
        "hop_31_rta",
        "hop_31_rtstddev",
    ],
)
graph_hop_32_packet_loss = graphs.Graph(
    name="hop_32_packet_loss",
    title=Title("Hop 32 packet loss"),
    compound_lines=["hop_32_pl"],
)
graph_hop_32_round_trip_average = graphs.Graph(
    name="hop_32_round_trip_average",
    title=Title("Hop 32 round trip average"),
    simple_lines=[
        "hop_32_rtmax",
        "hop_32_rtmin",
        "hop_32_rta",
        "hop_32_rtstddev",
    ],
)
graph_hop_33_packet_loss = graphs.Graph(
    name="hop_33_packet_loss",
    title=Title("Hop 33 packet loss"),
    compound_lines=["hop_33_pl"],
)
graph_hop_33_round_trip_average = graphs.Graph(
    name="hop_33_round_trip_average",
    title=Title("Hop 33 round trip average"),
    simple_lines=[
        "hop_33_rtmax",
        "hop_33_rtmin",
        "hop_33_rta",
        "hop_33_rtstddev",
    ],
)
graph_hop_34_packet_loss = graphs.Graph(
    name="hop_34_packet_loss",
    title=Title("Hop 34 packet loss"),
    compound_lines=["hop_34_pl"],
)
graph_hop_34_round_trip_average = graphs.Graph(
    name="hop_34_round_trip_average",
    title=Title("Hop 34 round trip average"),
    simple_lines=[
        "hop_34_rtmax",
        "hop_34_rtmin",
        "hop_34_rta",
        "hop_34_rtstddev",
    ],
)
graph_hop_35_packet_loss = graphs.Graph(
    name="hop_35_packet_loss",
    title=Title("Hop 35 packet loss"),
    compound_lines=["hop_35_pl"],
)
graph_hop_35_round_trip_average = graphs.Graph(
    name="hop_35_round_trip_average",
    title=Title("Hop 35 round trip average"),
    simple_lines=[
        "hop_35_rtmax",
        "hop_35_rtmin",
        "hop_35_rta",
        "hop_35_rtstddev",
    ],
)
graph_hop_36_packet_loss = graphs.Graph(
    name="hop_36_packet_loss",
    title=Title("Hop 36 packet loss"),
    compound_lines=["hop_36_pl"],
)
graph_hop_36_round_trip_average = graphs.Graph(
    name="hop_36_round_trip_average",
    title=Title("Hop 36 round trip average"),
    simple_lines=[
        "hop_36_rtmax",
        "hop_36_rtmin",
        "hop_36_rta",
        "hop_36_rtstddev",
    ],
)
graph_hop_37_packet_loss = graphs.Graph(
    name="hop_37_packet_loss",
    title=Title("Hop 37 packet loss"),
    compound_lines=["hop_37_pl"],
)
graph_hop_37_round_trip_average = graphs.Graph(
    name="hop_37_round_trip_average",
    title=Title("Hop 37 round trip average"),
    simple_lines=[
        "hop_37_rtmax",
        "hop_37_rtmin",
        "hop_37_rta",
        "hop_37_rtstddev",
    ],
)
graph_hop_38_packet_loss = graphs.Graph(
    name="hop_38_packet_loss",
    title=Title("Hop 38 packet loss"),
    compound_lines=["hop_38_pl"],
)
graph_hop_38_round_trip_average = graphs.Graph(
    name="hop_38_round_trip_average",
    title=Title("Hop 38 round trip average"),
    simple_lines=[
        "hop_38_rtmax",
        "hop_38_rtmin",
        "hop_38_rta",
        "hop_38_rtstddev",
    ],
)
graph_hop_39_packet_loss = graphs.Graph(
    name="hop_39_packet_loss",
    title=Title("Hop 39 packet loss"),
    compound_lines=["hop_39_pl"],
)
graph_hop_39_round_trip_average = graphs.Graph(
    name="hop_39_round_trip_average",
    title=Title("Hop 39 round trip average"),
    simple_lines=[
        "hop_39_rtmax",
        "hop_39_rtmin",
        "hop_39_rta",
        "hop_39_rtstddev",
    ],
)
graph_hop_3_packet_loss = graphs.Graph(
    name="hop_3_packet_loss",
    title=Title("Hop 3 packet loss"),
    compound_lines=["hop_3_pl"],
)
graph_hop_3_round_trip_average = graphs.Graph(
    name="hop_3_round_trip_average",
    title=Title("Hop 3 round trip average"),
    simple_lines=[
        "hop_3_rtmax",
        "hop_3_rtmin",
        "hop_3_rta",
        "hop_3_rtstddev",
    ],
)
graph_hop_40_packet_loss = graphs.Graph(
    name="hop_40_packet_loss",
    title=Title("Hop 40 packet loss"),
    compound_lines=["hop_40_pl"],
)
graph_hop_40_round_trip_average = graphs.Graph(
    name="hop_40_round_trip_average",
    title=Title("Hop 40 round trip average"),
    simple_lines=[
        "hop_40_rtmax",
        "hop_40_rtmin",
        "hop_40_rta",
        "hop_40_rtstddev",
    ],
)
graph_hop_41_packet_loss = graphs.Graph(
    name="hop_41_packet_loss",
    title=Title("Hop 41 packet loss"),
    compound_lines=["hop_41_pl"],
)
graph_hop_41_round_trip_average = graphs.Graph(
    name="hop_41_round_trip_average",
    title=Title("Hop 41 round trip average"),
    simple_lines=[
        "hop_41_rtmax",
        "hop_41_rtmin",
        "hop_41_rta",
        "hop_41_rtstddev",
    ],
)
graph_hop_42_packet_loss = graphs.Graph(
    name="hop_42_packet_loss",
    title=Title("Hop 42 packet loss"),
    compound_lines=["hop_42_pl"],
)
graph_hop_42_round_trip_average = graphs.Graph(
    name="hop_42_round_trip_average",
    title=Title("Hop 42 round trip average"),
    simple_lines=[
        "hop_42_rtmax",
        "hop_42_rtmin",
        "hop_42_rta",
        "hop_42_rtstddev",
    ],
)
graph_hop_43_packet_loss = graphs.Graph(
    name="hop_43_packet_loss",
    title=Title("Hop 43 packet loss"),
    compound_lines=["hop_43_pl"],
)
graph_hop_43_round_trip_average = graphs.Graph(
    name="hop_43_round_trip_average",
    title=Title("Hop 43 round trip average"),
    simple_lines=[
        "hop_43_rtmax",
        "hop_43_rtmin",
        "hop_43_rta",
        "hop_43_rtstddev",
    ],
)
graph_hop_44_packet_loss = graphs.Graph(
    name="hop_44_packet_loss",
    title=Title("Hop 44 packet loss"),
    compound_lines=["hop_44_pl"],
)
graph_hop_44_round_trip_average = graphs.Graph(
    name="hop_44_round_trip_average",
    title=Title("Hop 44 round trip average"),
    simple_lines=[
        "hop_44_rtmax",
        "hop_44_rtmin",
        "hop_44_rta",
        "hop_44_rtstddev",
    ],
)
graph_hop_4_packet_loss = graphs.Graph(
    name="hop_4_packet_loss",
    title=Title("Hop 4 packet loss"),
    compound_lines=["hop_4_pl"],
)
graph_hop_4_round_trip_average = graphs.Graph(
    name="hop_4_round_trip_average",
    title=Title("Hop 4 round trip average"),
    simple_lines=[
        "hop_4_rtmax",
        "hop_4_rtmin",
        "hop_4_rta",
        "hop_4_rtstddev",
    ],
)
graph_hop_5_packet_loss = graphs.Graph(
    name="hop_5_packet_loss",
    title=Title("Hop 5 packet loss"),
    compound_lines=["hop_5_pl"],
)
graph_hop_5_round_trip_average = graphs.Graph(
    name="hop_5_round_trip_average",
    title=Title("Hop 5 round trip average"),
    simple_lines=[
        "hop_5_rtmax",
        "hop_5_rtmin",
        "hop_5_rta",
        "hop_5_rtstddev",
    ],
)
graph_hop_6_packet_loss = graphs.Graph(
    name="hop_6_packet_loss",
    title=Title("Hop 6 packet loss"),
    compound_lines=["hop_6_pl"],
)
graph_hop_6_round_trip_average = graphs.Graph(
    name="hop_6_round_trip_average",
    title=Title("Hop 6 round trip average"),
    simple_lines=[
        "hop_6_rtmax",
        "hop_6_rtmin",
        "hop_6_rta",
        "hop_6_rtstddev",
    ],
)
graph_hop_7_packet_loss = graphs.Graph(
    name="hop_7_packet_loss",
    title=Title("Hop 7 packet loss"),
    compound_lines=["hop_7_pl"],
)
graph_hop_7_round_trip_average = graphs.Graph(
    name="hop_7_round_trip_average",
    title=Title("Hop 7 round trip average"),
    simple_lines=[
        "hop_7_rtmax",
        "hop_7_rtmin",
        "hop_7_rta",
        "hop_7_rtstddev",
    ],
)
graph_hop_8_packet_loss = graphs.Graph(
    name="hop_8_packet_loss",
    title=Title("Hop 8 packet loss"),
    compound_lines=["hop_8_pl"],
)
graph_hop_8_round_trip_average = graphs.Graph(
    name="hop_8_round_trip_average",
    title=Title("Hop 8 round trip average"),
    simple_lines=[
        "hop_8_rtmax",
        "hop_8_rtmin",
        "hop_8_rta",
        "hop_8_rtstddev",
    ],
)
graph_hop_9_packet_loss = graphs.Graph(
    name="hop_9_packet_loss",
    title=Title("Hop 9 packet loss"),
    compound_lines=["hop_9_pl"],
)
graph_hop_9_round_trip_average = graphs.Graph(
    name="hop_9_round_trip_average",
    title=Title("Hop 9 round trip average"),
    simple_lines=[
        "hop_9_rtmax",
        "hop_9_rtmin",
        "hop_9_rta",
        "hop_9_rtstddev",
    ],
)
graph_hop_response_time = graphs.Graph(
    name="hop_response_time",
    title=Title("Hop response times"),
    simple_lines=[
        metrics.Sum(
            title=Title("Hop response time"),
            summands=[
                "hop_1_response_time",
                "hop_2_response_time",
                "hop_3_response_time",
                "hop_4_response_time",
                "hop_5_response_time",
                "hop_6_response_time",
                "hop_7_response_time",
                "hop_8_response_time",
                "hop_9_response_time",
                "hop_10_response_time",
                "hop_11_response_time",
                "hop_12_response_time",
                "hop_13_response_time",
                "hop_14_response_time",
                "hop_15_response_time",
                "hop_16_response_time",
                "hop_17_response_time",
                "hop_18_response_time",
                "hop_19_response_time",
                "hop_20_response_time",
                "hop_21_response_time",
                "hop_22_response_time",
                "hop_23_response_time",
                "hop_24_response_time",
                "hop_25_response_time",
                "hop_26_response_time",
                "hop_27_response_time",
                "hop_28_response_time",
                "hop_29_response_time",
                "hop_30_response_time",
                "hop_31_response_time",
                "hop_32_response_time",
                "hop_33_response_time",
                "hop_34_response_time",
                "hop_35_response_time",
                "hop_36_response_time",
                "hop_37_response_time",
                "hop_38_response_time",
                "hop_39_response_time",
                "hop_40_response_time",
                "hop_41_response_time",
                "hop_42_response_time",
                "hop_43_response_time",
                "hop_44_response_time",
            ],
            color=metrics.Color.PURPLE,
        )
    ],
    optional=[
        "hop_2_response_time",
        "hop_3_response_time",
        "hop_4_response_time",
        "hop_5_response_time",
        "hop_6_response_time",
        "hop_7_response_time",
        "hop_8_response_time",
        "hop_9_response_time",
        "hop_10_response_time",
        "hop_11_response_time",
        "hop_12_response_time",
        "hop_13_response_time",
        "hop_14_response_time",
        "hop_15_response_time",
        "hop_16_response_time",
        "hop_17_response_time",
        "hop_18_response_time",
        "hop_19_response_time",
        "hop_20_response_time",
        "hop_21_response_time",
        "hop_22_response_time",
        "hop_23_response_time",
        "hop_24_response_time",
        "hop_25_response_time",
        "hop_26_response_time",
        "hop_27_response_time",
        "hop_28_response_time",
        "hop_29_response_time",
        "hop_30_response_time",
        "hop_31_response_time",
        "hop_32_response_time",
        "hop_33_response_time",
        "hop_34_response_time",
        "hop_35_response_time",
        "hop_36_response_time",
        "hop_37_response_time",
        "hop_38_response_time",
        "hop_39_response_time",
        "hop_40_response_time",
        "hop_41_response_time",
        "hop_42_response_time",
        "hop_43_response_time",
        "hop_44_response_time",
        "hop_45_response_time",
    ],
)
