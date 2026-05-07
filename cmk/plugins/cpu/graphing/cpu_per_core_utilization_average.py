#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_cpu_core_util_average_0 = metrics.Metric(
    name="cpu_core_util_average_0",
    title=Title("Average utilization core 0"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_average_1 = metrics.Metric(
    name="cpu_core_util_average_1",
    title=Title("Average utilization core 1"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_average_10 = metrics.Metric(
    name="cpu_core_util_average_10",
    title=Title("Average utilization core 10"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_average_100 = metrics.Metric(
    name="cpu_core_util_average_100",
    title=Title("Average utilization core 100"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_cpu_core_util_average_101 = metrics.Metric(
    name="cpu_core_util_average_101",
    title=Title("Average utilization core 101"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_average_102 = metrics.Metric(
    name="cpu_core_util_average_102",
    title=Title("Average utilization core 102"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_average_103 = metrics.Metric(
    name="cpu_core_util_average_103",
    title=Title("Average utilization core 103"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_cpu_core_util_average_104 = metrics.Metric(
    name="cpu_core_util_average_104",
    title=Title("Average utilization core 104"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_average_105 = metrics.Metric(
    name="cpu_core_util_average_105",
    title=Title("Average utilization core 105"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_106 = metrics.Metric(
    name="cpu_core_util_average_106",
    title=Title("Average utilization core 106"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_107 = metrics.Metric(
    name="cpu_core_util_average_107",
    title=Title("Average utilization core 107"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_cpu_core_util_average_108 = metrics.Metric(
    name="cpu_core_util_average_108",
    title=Title("Average utilization core 108"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_average_109 = metrics.Metric(
    name="cpu_core_util_average_109",
    title=Title("Average utilization core 109"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_average_11 = metrics.Metric(
    name="cpu_core_util_average_11",
    title=Title("Average utilization core 11"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_110 = metrics.Metric(
    name="cpu_core_util_average_110",
    title=Title("Average utilization core 110"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_cpu_core_util_average_111 = metrics.Metric(
    name="cpu_core_util_average_111",
    title=Title("Average utilization core 111"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_average_112 = metrics.Metric(
    name="cpu_core_util_average_112",
    title=Title("Average utilization core 112"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_113 = metrics.Metric(
    name="cpu_core_util_average_113",
    title=Title("Average utilization core 113"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_average_114 = metrics.Metric(
    name="cpu_core_util_average_114",
    title=Title("Average utilization core 114"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_cpu_core_util_average_115 = metrics.Metric(
    name="cpu_core_util_average_115",
    title=Title("Average utilization core 115"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_average_116 = metrics.Metric(
    name="cpu_core_util_average_116",
    title=Title("Average utilization core 116"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_average_117 = metrics.Metric(
    name="cpu_core_util_average_117",
    title=Title("Average utilization core 117"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_cpu_core_util_average_118 = metrics.Metric(
    name="cpu_core_util_average_118",
    title=Title("Average utilization core 118"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_cpu_core_util_average_119 = metrics.Metric(
    name="cpu_core_util_average_119",
    title=Title("Average utilization core 119"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_12 = metrics.Metric(
    name="cpu_core_util_average_12",
    title=Title("Average utilization core 12"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_cpu_core_util_average_120 = metrics.Metric(
    name="cpu_core_util_average_120",
    title=Title("Average utilization core 120"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_average_121 = metrics.Metric(
    name="cpu_core_util_average_121",
    title=Title("Average utilization core 121"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_cpu_core_util_average_122 = metrics.Metric(
    name="cpu_core_util_average_122",
    title=Title("Average utilization core 122"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_average_123 = metrics.Metric(
    name="cpu_core_util_average_123",
    title=Title("Average utilization core 123"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_124 = metrics.Metric(
    name="cpu_core_util_average_124",
    title=Title("Average utilization core 124"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_cpu_core_util_average_125 = metrics.Metric(
    name="cpu_core_util_average_125",
    title=Title("Average utilization core 125"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_average_126 = metrics.Metric(
    name="cpu_core_util_average_126",
    title=Title("Average utilization core 126"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_average_127 = metrics.Metric(
    name="cpu_core_util_average_127",
    title=Title("Average utilization core 127"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_average_13 = metrics.Metric(
    name="cpu_core_util_average_13",
    title=Title("Average utilization core 13"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_14 = metrics.Metric(
    name="cpu_core_util_average_14",
    title=Title("Average utilization core 14"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_average_15 = metrics.Metric(
    name="cpu_core_util_average_15",
    title=Title("Average utilization core 15"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_average_16 = metrics.Metric(
    name="cpu_core_util_average_16",
    title=Title("Average utilization core 16"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_cpu_core_util_average_17 = metrics.Metric(
    name="cpu_core_util_average_17",
    title=Title("Average utilization core 17"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_average_18 = metrics.Metric(
    name="cpu_core_util_average_18",
    title=Title("Average utilization core 18"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_average_19 = metrics.Metric(
    name="cpu_core_util_average_19",
    title=Title("Average utilization core 19"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_2 = metrics.Metric(
    name="cpu_core_util_average_2",
    title=Title("Average utilization core 2"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_average_20 = metrics.Metric(
    name="cpu_core_util_average_20",
    title=Title("Average utilization core 20"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_cpu_core_util_average_21 = metrics.Metric(
    name="cpu_core_util_average_21",
    title=Title("Average utilization core 21"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_22 = metrics.Metric(
    name="cpu_core_util_average_22",
    title=Title("Average utilization core 22"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_average_23 = metrics.Metric(
    name="cpu_core_util_average_23",
    title=Title("Average utilization core 23"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_average_24 = metrics.Metric(
    name="cpu_core_util_average_24",
    title=Title("Average utilization core 24"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_average_25 = metrics.Metric(
    name="cpu_core_util_average_25",
    title=Title("Average utilization core 25"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_average_26 = metrics.Metric(
    name="cpu_core_util_average_26",
    title=Title("Average utilization core 26"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_average_27 = metrics.Metric(
    name="cpu_core_util_average_27",
    title=Title("Average utilization core 27"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_average_28 = metrics.Metric(
    name="cpu_core_util_average_28",
    title=Title("Average utilization core 28"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PINK,
)
metric_cpu_core_util_average_29 = metrics.Metric(
    name="cpu_core_util_average_29",
    title=Title("Average utilization core 29"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_3 = metrics.Metric(
    name="cpu_core_util_average_3",
    title=Title("Average utilization core 3"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_average_30 = metrics.Metric(
    name="cpu_core_util_average_30",
    title=Title("Average utilization core 30"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_average_31 = metrics.Metric(
    name="cpu_core_util_average_31",
    title=Title("Average utilization core 31"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)
metric_cpu_core_util_average_32 = metrics.Metric(
    name="cpu_core_util_average_32",
    title=Title("Average utilization core 32"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_average_33 = metrics.Metric(
    name="cpu_core_util_average_33",
    title=Title("Average utilization core 33"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_average_34 = metrics.Metric(
    name="cpu_core_util_average_34",
    title=Title("Average utilization core 34"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_average_35 = metrics.Metric(
    name="cpu_core_util_average_35",
    title=Title("Average utilization core 35"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_36 = metrics.Metric(
    name="cpu_core_util_average_36",
    title=Title("Average utilization core 36"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_cpu_core_util_average_37 = metrics.Metric(
    name="cpu_core_util_average_37",
    title=Title("Average utilization core 37"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_38 = metrics.Metric(
    name="cpu_core_util_average_38",
    title=Title("Average utilization core 38"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_average_39 = metrics.Metric(
    name="cpu_core_util_average_39",
    title=Title("Average utilization core 39"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_average_4 = metrics.Metric(
    name="cpu_core_util_average_4",
    title=Title("Average utilization core 4"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PINK,
)
metric_cpu_core_util_average_40 = metrics.Metric(
    name="cpu_core_util_average_40",
    title=Title("Average utilization core 40"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_cpu_core_util_average_41 = metrics.Metric(
    name="cpu_core_util_average_41",
    title=Title("Average utilization core 41"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_average_42 = metrics.Metric(
    name="cpu_core_util_average_42",
    title=Title("Average utilization core 42"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_average_43 = metrics.Metric(
    name="cpu_core_util_average_43",
    title=Title("Average utilization core 43"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_44 = metrics.Metric(
    name="cpu_core_util_average_44",
    title=Title("Average utilization core 44"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_cpu_core_util_average_45 = metrics.Metric(
    name="cpu_core_util_average_45",
    title=Title("Average utilization core 45"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_46 = metrics.Metric(
    name="cpu_core_util_average_46",
    title=Title("Average utilization core 46"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_average_47 = metrics.Metric(
    name="cpu_core_util_average_47",
    title=Title("Average utilization core 47"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_average_48 = metrics.Metric(
    name="cpu_core_util_average_48",
    title=Title("Average utilization core 48"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.RED,
)
metric_cpu_core_util_average_49 = metrics.Metric(
    name="cpu_core_util_average_49",
    title=Title("Average utilization core 49"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_cpu_core_util_average_5 = metrics.Metric(
    name="cpu_core_util_average_5",
    title=Title("Average utilization core 5"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_50 = metrics.Metric(
    name="cpu_core_util_average_50",
    title=Title("Average utilization core 50"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_51 = metrics.Metric(
    name="cpu_core_util_average_51",
    title=Title("Average utilization core 51"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_average_52 = metrics.Metric(
    name="cpu_core_util_average_52",
    title=Title("Average utilization core 52"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_average_53 = metrics.Metric(
    name="cpu_core_util_average_53",
    title=Title("Average utilization core 53"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_average_54 = metrics.Metric(
    name="cpu_core_util_average_54",
    title=Title("Average utilization core 54"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GRAY,
)
metric_cpu_core_util_average_55 = metrics.Metric(
    name="cpu_core_util_average_55",
    title=Title("Average utilization core 55"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_average_56 = metrics.Metric(
    name="cpu_core_util_average_56",
    title=Title("Average utilization core 56"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_57 = metrics.Metric(
    name="cpu_core_util_average_57",
    title=Title("Average utilization core 57"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_58 = metrics.Metric(
    name="cpu_core_util_average_58",
    title=Title("Average utilization core 58"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_59 = metrics.Metric(
    name="cpu_core_util_average_59",
    title=Title("Average utilization core 59"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_average_6 = metrics.Metric(
    name="cpu_core_util_average_6",
    title=Title("Average utilization core 6"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_average_60 = metrics.Metric(
    name="cpu_core_util_average_60",
    title=Title("Average utilization core 60"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_average_61 = metrics.Metric(
    name="cpu_core_util_average_61",
    title=Title("Average utilization core 61"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GRAY,
)
metric_cpu_core_util_average_62 = metrics.Metric(
    name="cpu_core_util_average_62",
    title=Title("Average utilization core 62"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_average_63 = metrics.Metric(
    name="cpu_core_util_average_63",
    title=Title("Average utilization core 63"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_64 = metrics.Metric(
    name="cpu_core_util_average_64",
    title=Title("Average utilization core 64"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_65 = metrics.Metric(
    name="cpu_core_util_average_65",
    title=Title("Average utilization core 65"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_66 = metrics.Metric(
    name="cpu_core_util_average_66",
    title=Title("Average utilization core 66"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_average_67 = metrics.Metric(
    name="cpu_core_util_average_67",
    title=Title("Average utilization core 67"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_average_68 = metrics.Metric(
    name="cpu_core_util_average_68",
    title=Title("Average utilization core 68"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GRAY,
)
metric_cpu_core_util_average_69 = metrics.Metric(
    name="cpu_core_util_average_69",
    title=Title("Average utilization core 69"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_average_7 = metrics.Metric(
    name="cpu_core_util_average_7",
    title=Title("Average utilization core 7"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)
metric_cpu_core_util_average_70 = metrics.Metric(
    name="cpu_core_util_average_70",
    title=Title("Average utilization core 70"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_71 = metrics.Metric(
    name="cpu_core_util_average_71",
    title=Title("Average utilization core 71"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_72 = metrics.Metric(
    name="cpu_core_util_average_72",
    title=Title("Average utilization core 72"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_73 = metrics.Metric(
    name="cpu_core_util_average_73",
    title=Title("Average utilization core 73"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_average_74 = metrics.Metric(
    name="cpu_core_util_average_74",
    title=Title("Average utilization core 74"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_average_75 = metrics.Metric(
    name="cpu_core_util_average_75",
    title=Title("Average utilization core 75"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GRAY,
)
metric_cpu_core_util_average_76 = metrics.Metric(
    name="cpu_core_util_average_76",
    title=Title("Average utilization core 76"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_average_77 = metrics.Metric(
    name="cpu_core_util_average_77",
    title=Title("Average utilization core 77"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_78 = metrics.Metric(
    name="cpu_core_util_average_78",
    title=Title("Average utilization core 78"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_79 = metrics.Metric(
    name="cpu_core_util_average_79",
    title=Title("Average utilization core 79"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_8 = metrics.Metric(
    name="cpu_core_util_average_8",
    title=Title("Average utilization core 8"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_average_80 = metrics.Metric(
    name="cpu_core_util_average_80",
    title=Title("Average utilization core 80"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_average_81 = metrics.Metric(
    name="cpu_core_util_average_81",
    title=Title("Average utilization core 81"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_average_82 = metrics.Metric(
    name="cpu_core_util_average_82",
    title=Title("Average utilization core 82"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GRAY,
)
metric_cpu_core_util_average_83 = metrics.Metric(
    name="cpu_core_util_average_83",
    title=Title("Average utilization core 83"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_average_84 = metrics.Metric(
    name="cpu_core_util_average_84",
    title=Title("Average utilization core 84"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_85 = metrics.Metric(
    name="cpu_core_util_average_85",
    title=Title("Average utilization core 85"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_86 = metrics.Metric(
    name="cpu_core_util_average_86",
    title=Title("Average utilization core 86"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_87 = metrics.Metric(
    name="cpu_core_util_average_87",
    title=Title("Average utilization core 87"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_average_88 = metrics.Metric(
    name="cpu_core_util_average_88",
    title=Title("Average utilization core 88"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_average_89 = metrics.Metric(
    name="cpu_core_util_average_89",
    title=Title("Average utilization core 89"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GRAY,
)
metric_cpu_core_util_average_9 = metrics.Metric(
    name="cpu_core_util_average_9",
    title=Title("Average utilization core 9"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_average_90 = metrics.Metric(
    name="cpu_core_util_average_90",
    title=Title("Average utilization core 90"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_average_91 = metrics.Metric(
    name="cpu_core_util_average_91",
    title=Title("Average utilization core 91"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_92 = metrics.Metric(
    name="cpu_core_util_average_92",
    title=Title("Average utilization core 92"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_average_93 = metrics.Metric(
    name="cpu_core_util_average_93",
    title=Title("Average utilization core 93"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_average_94 = metrics.Metric(
    name="cpu_core_util_average_94",
    title=Title("Average utilization core 94"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_average_95 = metrics.Metric(
    name="cpu_core_util_average_95",
    title=Title("Average utilization core 95"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_average_96 = metrics.Metric(
    name="cpu_core_util_average_96",
    title=Title("Average utilization core 96"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_cpu_core_util_average_97 = metrics.Metric(
    name="cpu_core_util_average_97",
    title=Title("Average utilization core 97"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_average_98 = metrics.Metric(
    name="cpu_core_util_average_98",
    title=Title("Average utilization core 98"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_average_99 = metrics.Metric(
    name="cpu_core_util_average_99",
    title=Title("Average utilization core 99"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)

# TODO we should review this graph if it really makes sense
graph_per_core_utilization_average = graphs.Graph(
    name="per_core_utilization_average",
    title=Title("Average utilization per core"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    simple_lines=[
        "cpu_core_util_average_0",
        "cpu_core_util_average_1",
        "cpu_core_util_average_2",
        "cpu_core_util_average_3",
        "cpu_core_util_average_4",
        "cpu_core_util_average_5",
        "cpu_core_util_average_6",
        "cpu_core_util_average_7",
        "cpu_core_util_average_8",
        "cpu_core_util_average_9",
        "cpu_core_util_average_10",
        "cpu_core_util_average_11",
        "cpu_core_util_average_12",
        "cpu_core_util_average_13",
        "cpu_core_util_average_14",
        "cpu_core_util_average_15",
        "cpu_core_util_average_16",
        "cpu_core_util_average_17",
        "cpu_core_util_average_18",
        "cpu_core_util_average_19",
        "cpu_core_util_average_20",
        "cpu_core_util_average_21",
        "cpu_core_util_average_22",
        "cpu_core_util_average_23",
        "cpu_core_util_average_24",
        "cpu_core_util_average_25",
        "cpu_core_util_average_26",
        "cpu_core_util_average_27",
        "cpu_core_util_average_28",
        "cpu_core_util_average_29",
        "cpu_core_util_average_30",
        "cpu_core_util_average_31",
        "cpu_core_util_average_32",
        "cpu_core_util_average_33",
        "cpu_core_util_average_34",
        "cpu_core_util_average_35",
        "cpu_core_util_average_36",
        "cpu_core_util_average_37",
        "cpu_core_util_average_38",
        "cpu_core_util_average_39",
        "cpu_core_util_average_40",
        "cpu_core_util_average_41",
        "cpu_core_util_average_42",
        "cpu_core_util_average_43",
        "cpu_core_util_average_44",
        "cpu_core_util_average_45",
        "cpu_core_util_average_46",
        "cpu_core_util_average_47",
        "cpu_core_util_average_48",
        "cpu_core_util_average_49",
        "cpu_core_util_average_50",
        "cpu_core_util_average_51",
        "cpu_core_util_average_52",
        "cpu_core_util_average_53",
        "cpu_core_util_average_54",
        "cpu_core_util_average_55",
        "cpu_core_util_average_56",
        "cpu_core_util_average_57",
        "cpu_core_util_average_58",
        "cpu_core_util_average_59",
        "cpu_core_util_average_60",
        "cpu_core_util_average_61",
        "cpu_core_util_average_62",
        "cpu_core_util_average_63",
        "cpu_core_util_average_64",
        "cpu_core_util_average_65",
        "cpu_core_util_average_66",
        "cpu_core_util_average_67",
        "cpu_core_util_average_68",
        "cpu_core_util_average_69",
        "cpu_core_util_average_70",
        "cpu_core_util_average_71",
        "cpu_core_util_average_72",
        "cpu_core_util_average_73",
        "cpu_core_util_average_74",
        "cpu_core_util_average_75",
        "cpu_core_util_average_76",
        "cpu_core_util_average_77",
        "cpu_core_util_average_78",
        "cpu_core_util_average_79",
        "cpu_core_util_average_80",
        "cpu_core_util_average_81",
        "cpu_core_util_average_82",
        "cpu_core_util_average_83",
        "cpu_core_util_average_84",
        "cpu_core_util_average_85",
        "cpu_core_util_average_86",
        "cpu_core_util_average_87",
        "cpu_core_util_average_88",
        "cpu_core_util_average_89",
        "cpu_core_util_average_90",
        "cpu_core_util_average_91",
        "cpu_core_util_average_92",
        "cpu_core_util_average_93",
        "cpu_core_util_average_94",
        "cpu_core_util_average_95",
        "cpu_core_util_average_96",
        "cpu_core_util_average_97",
        "cpu_core_util_average_98",
        "cpu_core_util_average_99",
        "cpu_core_util_average_100",
        "cpu_core_util_average_101",
        "cpu_core_util_average_102",
        "cpu_core_util_average_103",
        "cpu_core_util_average_104",
        "cpu_core_util_average_105",
        "cpu_core_util_average_106",
        "cpu_core_util_average_107",
        "cpu_core_util_average_108",
        "cpu_core_util_average_109",
        "cpu_core_util_average_110",
        "cpu_core_util_average_111",
        "cpu_core_util_average_112",
        "cpu_core_util_average_113",
        "cpu_core_util_average_114",
        "cpu_core_util_average_115",
        "cpu_core_util_average_116",
        "cpu_core_util_average_117",
        "cpu_core_util_average_118",
        "cpu_core_util_average_119",
        "cpu_core_util_average_120",
        "cpu_core_util_average_121",
        "cpu_core_util_average_122",
        "cpu_core_util_average_123",
        "cpu_core_util_average_124",
        "cpu_core_util_average_125",
        "cpu_core_util_average_126",
        "cpu_core_util_average_127",
    ],
    optional=[
        "cpu_core_util_average_2",
        "cpu_core_util_average_3",
        "cpu_core_util_average_4",
        "cpu_core_util_average_5",
        "cpu_core_util_average_6",
        "cpu_core_util_average_7",
        "cpu_core_util_average_8",
        "cpu_core_util_average_9",
        "cpu_core_util_average_10",
        "cpu_core_util_average_11",
        "cpu_core_util_average_12",
        "cpu_core_util_average_13",
        "cpu_core_util_average_14",
        "cpu_core_util_average_15",
        "cpu_core_util_average_16",
        "cpu_core_util_average_17",
        "cpu_core_util_average_18",
        "cpu_core_util_average_19",
        "cpu_core_util_average_20",
        "cpu_core_util_average_21",
        "cpu_core_util_average_22",
        "cpu_core_util_average_23",
        "cpu_core_util_average_24",
        "cpu_core_util_average_25",
        "cpu_core_util_average_26",
        "cpu_core_util_average_27",
        "cpu_core_util_average_28",
        "cpu_core_util_average_29",
        "cpu_core_util_average_30",
        "cpu_core_util_average_31",
        "cpu_core_util_average_32",
        "cpu_core_util_average_33",
        "cpu_core_util_average_34",
        "cpu_core_util_average_35",
        "cpu_core_util_average_36",
        "cpu_core_util_average_37",
        "cpu_core_util_average_38",
        "cpu_core_util_average_39",
        "cpu_core_util_average_40",
        "cpu_core_util_average_41",
        "cpu_core_util_average_42",
        "cpu_core_util_average_43",
        "cpu_core_util_average_44",
        "cpu_core_util_average_45",
        "cpu_core_util_average_46",
        "cpu_core_util_average_47",
        "cpu_core_util_average_48",
        "cpu_core_util_average_49",
        "cpu_core_util_average_50",
        "cpu_core_util_average_51",
        "cpu_core_util_average_52",
        "cpu_core_util_average_53",
        "cpu_core_util_average_54",
        "cpu_core_util_average_55",
        "cpu_core_util_average_56",
        "cpu_core_util_average_57",
        "cpu_core_util_average_58",
        "cpu_core_util_average_59",
        "cpu_core_util_average_60",
        "cpu_core_util_average_61",
        "cpu_core_util_average_62",
        "cpu_core_util_average_63",
        "cpu_core_util_average_64",
        "cpu_core_util_average_65",
        "cpu_core_util_average_66",
        "cpu_core_util_average_67",
        "cpu_core_util_average_68",
        "cpu_core_util_average_69",
        "cpu_core_util_average_70",
        "cpu_core_util_average_71",
        "cpu_core_util_average_72",
        "cpu_core_util_average_73",
        "cpu_core_util_average_74",
        "cpu_core_util_average_75",
        "cpu_core_util_average_76",
        "cpu_core_util_average_77",
        "cpu_core_util_average_78",
        "cpu_core_util_average_79",
        "cpu_core_util_average_80",
        "cpu_core_util_average_81",
        "cpu_core_util_average_82",
        "cpu_core_util_average_83",
        "cpu_core_util_average_84",
        "cpu_core_util_average_85",
        "cpu_core_util_average_86",
        "cpu_core_util_average_87",
        "cpu_core_util_average_88",
        "cpu_core_util_average_89",
        "cpu_core_util_average_90",
        "cpu_core_util_average_91",
        "cpu_core_util_average_92",
        "cpu_core_util_average_93",
        "cpu_core_util_average_94",
        "cpu_core_util_average_95",
        "cpu_core_util_average_96",
        "cpu_core_util_average_97",
        "cpu_core_util_average_98",
        "cpu_core_util_average_99",
        "cpu_core_util_average_100",
        "cpu_core_util_average_101",
        "cpu_core_util_average_102",
        "cpu_core_util_average_103",
        "cpu_core_util_average_104",
        "cpu_core_util_average_105",
        "cpu_core_util_average_106",
        "cpu_core_util_average_107",
        "cpu_core_util_average_108",
        "cpu_core_util_average_109",
        "cpu_core_util_average_110",
        "cpu_core_util_average_111",
        "cpu_core_util_average_112",
        "cpu_core_util_average_113",
        "cpu_core_util_average_114",
        "cpu_core_util_average_115",
        "cpu_core_util_average_116",
        "cpu_core_util_average_117",
        "cpu_core_util_average_118",
        "cpu_core_util_average_119",
        "cpu_core_util_average_120",
        "cpu_core_util_average_121",
        "cpu_core_util_average_122",
        "cpu_core_util_average_123",
        "cpu_core_util_average_124",
        "cpu_core_util_average_125",
        "cpu_core_util_average_126",
        "cpu_core_util_average_127",
    ],
)
