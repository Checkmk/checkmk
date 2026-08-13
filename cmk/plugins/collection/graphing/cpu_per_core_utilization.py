#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_cpu_core_util_0 = metrics.Metric(
    name="cpu_core_util_0",
    title=Title("Utilization core 0"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_1 = metrics.Metric(
    name="cpu_core_util_1",
    title=Title("Utilization core 1"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_10 = metrics.Metric(
    name="cpu_core_util_10",
    title=Title("Utilization core 10"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_100 = metrics.Metric(
    name="cpu_core_util_100",
    title=Title("Utilization core 100"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_cpu_core_util_101 = metrics.Metric(
    name="cpu_core_util_101",
    title=Title("Utilization core 101"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_102 = metrics.Metric(
    name="cpu_core_util_102",
    title=Title("Utilization core 102"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_103 = metrics.Metric(
    name="cpu_core_util_103",
    title=Title("Utilization core 103"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_cpu_core_util_104 = metrics.Metric(
    name="cpu_core_util_104",
    title=Title("Utilization core 104"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_105 = metrics.Metric(
    name="cpu_core_util_105",
    title=Title("Utilization core 105"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_106 = metrics.Metric(
    name="cpu_core_util_106",
    title=Title("Utilization core 106"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_107 = metrics.Metric(
    name="cpu_core_util_107",
    title=Title("Utilization core 107"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_cpu_core_util_108 = metrics.Metric(
    name="cpu_core_util_108",
    title=Title("Utilization core 108"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_109 = metrics.Metric(
    name="cpu_core_util_109",
    title=Title("Utilization core 109"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_11 = metrics.Metric(
    name="cpu_core_util_11",
    title=Title("Utilization core 11"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_110 = metrics.Metric(
    name="cpu_core_util_110",
    title=Title("Utilization core 110"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_cpu_core_util_111 = metrics.Metric(
    name="cpu_core_util_111",
    title=Title("Utilization core 111"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_112 = metrics.Metric(
    name="cpu_core_util_112",
    title=Title("Utilization core 112"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_113 = metrics.Metric(
    name="cpu_core_util_113",
    title=Title("Utilization core 113"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_114 = metrics.Metric(
    name="cpu_core_util_114",
    title=Title("Utilization core 114"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_cpu_core_util_115 = metrics.Metric(
    name="cpu_core_util_115",
    title=Title("Utilization core 115"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_116 = metrics.Metric(
    name="cpu_core_util_116",
    title=Title("Utilization core 116"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_117 = metrics.Metric(
    name="cpu_core_util_117",
    title=Title("Utilization core 117"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_cpu_core_util_118 = metrics.Metric(
    name="cpu_core_util_118",
    title=Title("Utilization core 118"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_cpu_core_util_119 = metrics.Metric(
    name="cpu_core_util_119",
    title=Title("Utilization core 119"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_12 = metrics.Metric(
    name="cpu_core_util_12",
    title=Title("Utilization core 12"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_cpu_core_util_120 = metrics.Metric(
    name="cpu_core_util_120",
    title=Title("Utilization core 120"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_121 = metrics.Metric(
    name="cpu_core_util_121",
    title=Title("Utilization core 121"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_cpu_core_util_122 = metrics.Metric(
    name="cpu_core_util_122",
    title=Title("Utilization core 122"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_123 = metrics.Metric(
    name="cpu_core_util_123",
    title=Title("Utilization core 123"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_124 = metrics.Metric(
    name="cpu_core_util_124",
    title=Title("Utilization core 124"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_cpu_core_util_125 = metrics.Metric(
    name="cpu_core_util_125",
    title=Title("Utilization core 125"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_126 = metrics.Metric(
    name="cpu_core_util_126",
    title=Title("Utilization core 126"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_127 = metrics.Metric(
    name="cpu_core_util_127",
    title=Title("Utilization core 127"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_cpu_core_util_13 = metrics.Metric(
    name="cpu_core_util_13",
    title=Title("Utilization core 13"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_14 = metrics.Metric(
    name="cpu_core_util_14",
    title=Title("Utilization core 14"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_15 = metrics.Metric(
    name="cpu_core_util_15",
    title=Title("Utilization core 15"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_16 = metrics.Metric(
    name="cpu_core_util_16",
    title=Title("Utilization core 16"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_cpu_core_util_17 = metrics.Metric(
    name="cpu_core_util_17",
    title=Title("Utilization core 17"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_18 = metrics.Metric(
    name="cpu_core_util_18",
    title=Title("Utilization core 18"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_19 = metrics.Metric(
    name="cpu_core_util_19",
    title=Title("Utilization core 19"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_2 = metrics.Metric(
    name="cpu_core_util_2",
    title=Title("Utilization core 2"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_20 = metrics.Metric(
    name="cpu_core_util_20",
    title=Title("Utilization core 20"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_cpu_core_util_21 = metrics.Metric(
    name="cpu_core_util_21",
    title=Title("Utilization core 21"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_22 = metrics.Metric(
    name="cpu_core_util_22",
    title=Title("Utilization core 22"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_23 = metrics.Metric(
    name="cpu_core_util_23",
    title=Title("Utilization core 23"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_24 = metrics.Metric(
    name="cpu_core_util_24",
    title=Title("Utilization core 24"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_25 = metrics.Metric(
    name="cpu_core_util_25",
    title=Title("Utilization core 25"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_26 = metrics.Metric(
    name="cpu_core_util_26",
    title=Title("Utilization core 26"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_27 = metrics.Metric(
    name="cpu_core_util_27",
    title=Title("Utilization core 27"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_28 = metrics.Metric(
    name="cpu_core_util_28",
    title=Title("Utilization core 28"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PINK,
)
metric_cpu_core_util_29 = metrics.Metric(
    name="cpu_core_util_29",
    title=Title("Utilization core 29"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_3 = metrics.Metric(
    name="cpu_core_util_3",
    title=Title("Utilization core 3"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_30 = metrics.Metric(
    name="cpu_core_util_30",
    title=Title("Utilization core 30"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_31 = metrics.Metric(
    name="cpu_core_util_31",
    title=Title("Utilization core 31"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)
metric_cpu_core_util_32 = metrics.Metric(
    name="cpu_core_util_32",
    title=Title("Utilization core 32"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_33 = metrics.Metric(
    name="cpu_core_util_33",
    title=Title("Utilization core 33"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_34 = metrics.Metric(
    name="cpu_core_util_34",
    title=Title("Utilization core 34"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_35 = metrics.Metric(
    name="cpu_core_util_35",
    title=Title("Utilization core 35"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_36 = metrics.Metric(
    name="cpu_core_util_36",
    title=Title("Utilization core 36"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_cpu_core_util_37 = metrics.Metric(
    name="cpu_core_util_37",
    title=Title("Utilization core 37"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_38 = metrics.Metric(
    name="cpu_core_util_38",
    title=Title("Utilization core 38"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_39 = metrics.Metric(
    name="cpu_core_util_39",
    title=Title("Utilization core 39"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_4 = metrics.Metric(
    name="cpu_core_util_4",
    title=Title("Utilization core 4"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PINK,
)
metric_cpu_core_util_40 = metrics.Metric(
    name="cpu_core_util_40",
    title=Title("Utilization core 40"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_cpu_core_util_41 = metrics.Metric(
    name="cpu_core_util_41",
    title=Title("Utilization core 41"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_42 = metrics.Metric(
    name="cpu_core_util_42",
    title=Title("Utilization core 42"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_43 = metrics.Metric(
    name="cpu_core_util_43",
    title=Title("Utilization core 43"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_44 = metrics.Metric(
    name="cpu_core_util_44",
    title=Title("Utilization core 44"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_cpu_core_util_45 = metrics.Metric(
    name="cpu_core_util_45",
    title=Title("Utilization core 45"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_46 = metrics.Metric(
    name="cpu_core_util_46",
    title=Title("Utilization core 46"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_cpu_core_util_47 = metrics.Metric(
    name="cpu_core_util_47",
    title=Title("Utilization core 47"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_cpu_core_util_48 = metrics.Metric(
    name="cpu_core_util_48",
    title=Title("Utilization core 48"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.RED,
)
metric_cpu_core_util_49 = metrics.Metric(
    name="cpu_core_util_49",
    title=Title("Utilization core 49"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_cpu_core_util_5 = metrics.Metric(
    name="cpu_core_util_5",
    title=Title("Utilization core 5"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_50 = metrics.Metric(
    name="cpu_core_util_50",
    title=Title("Utilization core 50"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_51 = metrics.Metric(
    name="cpu_core_util_51",
    title=Title("Utilization core 51"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_52 = metrics.Metric(
    name="cpu_core_util_52",
    title=Title("Utilization core 52"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_53 = metrics.Metric(
    name="cpu_core_util_53",
    title=Title("Utilization core 53"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_54 = metrics.Metric(
    name="cpu_core_util_54",
    title=Title("Utilization core 54"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GRAY,
)
metric_cpu_core_util_55 = metrics.Metric(
    name="cpu_core_util_55",
    title=Title("Utilization core 55"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_56 = metrics.Metric(
    name="cpu_core_util_56",
    title=Title("Utilization core 56"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_57 = metrics.Metric(
    name="cpu_core_util_57",
    title=Title("Utilization core 57"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_58 = metrics.Metric(
    name="cpu_core_util_58",
    title=Title("Utilization core 58"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_59 = metrics.Metric(
    name="cpu_core_util_59",
    title=Title("Utilization core 59"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_6 = metrics.Metric(
    name="cpu_core_util_6",
    title=Title("Utilization core 6"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_60 = metrics.Metric(
    name="cpu_core_util_60",
    title=Title("Utilization core 60"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_61 = metrics.Metric(
    name="cpu_core_util_61",
    title=Title("Utilization core 61"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GRAY,
)
metric_cpu_core_util_62 = metrics.Metric(
    name="cpu_core_util_62",
    title=Title("Utilization core 62"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_63 = metrics.Metric(
    name="cpu_core_util_63",
    title=Title("Utilization core 63"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_64 = metrics.Metric(
    name="cpu_core_util_64",
    title=Title("Utilization core 64"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_65 = metrics.Metric(
    name="cpu_core_util_65",
    title=Title("Utilization core 65"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_66 = metrics.Metric(
    name="cpu_core_util_66",
    title=Title("Utilization core 66"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_67 = metrics.Metric(
    name="cpu_core_util_67",
    title=Title("Utilization core 67"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_cpu_core_util_68 = metrics.Metric(
    name="cpu_core_util_68",
    title=Title("Utilization core 68"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GRAY,
)
metric_cpu_core_util_69 = metrics.Metric(
    name="cpu_core_util_69",
    title=Title("Utilization core 69"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_7 = metrics.Metric(
    name="cpu_core_util_7",
    title=Title("Utilization core 7"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)
metric_cpu_core_util_70 = metrics.Metric(
    name="cpu_core_util_70",
    title=Title("Utilization core 70"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_71 = metrics.Metric(
    name="cpu_core_util_71",
    title=Title("Utilization core 71"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_72 = metrics.Metric(
    name="cpu_core_util_72",
    title=Title("Utilization core 72"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_73 = metrics.Metric(
    name="cpu_core_util_73",
    title=Title("Utilization core 73"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_74 = metrics.Metric(
    name="cpu_core_util_74",
    title=Title("Utilization core 74"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_75 = metrics.Metric(
    name="cpu_core_util_75",
    title=Title("Utilization core 75"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GRAY,
)
metric_cpu_core_util_76 = metrics.Metric(
    name="cpu_core_util_76",
    title=Title("Utilization core 76"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_77 = metrics.Metric(
    name="cpu_core_util_77",
    title=Title("Utilization core 77"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_78 = metrics.Metric(
    name="cpu_core_util_78",
    title=Title("Utilization core 78"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_79 = metrics.Metric(
    name="cpu_core_util_79",
    title=Title("Utilization core 79"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_8 = metrics.Metric(
    name="cpu_core_util_8",
    title=Title("Utilization core 8"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_cpu_core_util_80 = metrics.Metric(
    name="cpu_core_util_80",
    title=Title("Utilization core 80"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_81 = metrics.Metric(
    name="cpu_core_util_81",
    title=Title("Utilization core 81"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_82 = metrics.Metric(
    name="cpu_core_util_82",
    title=Title("Utilization core 82"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GRAY,
)
metric_cpu_core_util_83 = metrics.Metric(
    name="cpu_core_util_83",
    title=Title("Utilization core 83"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_84 = metrics.Metric(
    name="cpu_core_util_84",
    title=Title("Utilization core 84"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_85 = metrics.Metric(
    name="cpu_core_util_85",
    title=Title("Utilization core 85"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_86 = metrics.Metric(
    name="cpu_core_util_86",
    title=Title("Utilization core 86"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_87 = metrics.Metric(
    name="cpu_core_util_87",
    title=Title("Utilization core 87"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_88 = metrics.Metric(
    name="cpu_core_util_88",
    title=Title("Utilization core 88"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_89 = metrics.Metric(
    name="cpu_core_util_89",
    title=Title("Utilization core 89"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GRAY,
)
metric_cpu_core_util_9 = metrics.Metric(
    name="cpu_core_util_9",
    title=Title("Utilization core 9"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_cpu_core_util_90 = metrics.Metric(
    name="cpu_core_util_90",
    title=Title("Utilization core 90"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_91 = metrics.Metric(
    name="cpu_core_util_91",
    title=Title("Utilization core 91"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_92 = metrics.Metric(
    name="cpu_core_util_92",
    title=Title("Utilization core 92"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_cpu_core_util_93 = metrics.Metric(
    name="cpu_core_util_93",
    title=Title("Utilization core 93"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_cpu_core_util_94 = metrics.Metric(
    name="cpu_core_util_94",
    title=Title("Utilization core 94"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PURPLE,
)
metric_cpu_core_util_95 = metrics.Metric(
    name="cpu_core_util_95",
    title=Title("Utilization core 95"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_CYAN,
)
metric_cpu_core_util_96 = metrics.Metric(
    name="cpu_core_util_96",
    title=Title("Utilization core 96"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GRAY,
)
metric_cpu_core_util_97 = metrics.Metric(
    name="cpu_core_util_97",
    title=Title("Utilization core 97"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_RED,
)
metric_cpu_core_util_98 = metrics.Metric(
    name="cpu_core_util_98",
    title=Title("Utilization core 98"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_cpu_core_util_99 = metrics.Metric(
    name="cpu_core_util_99",
    title=Title("Utilization core 99"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)

# TODO we should review this graph if it really makes sense
graph_per_core_utilization = graphs.Graph(
    name="per_core_utilization",
    title=Title("Per core utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    simple_lines=[
        "cpu_core_util_0",
        "cpu_core_util_1",
        "cpu_core_util_2",
        "cpu_core_util_3",
        "cpu_core_util_4",
        "cpu_core_util_5",
        "cpu_core_util_6",
        "cpu_core_util_7",
        "cpu_core_util_8",
        "cpu_core_util_9",
        "cpu_core_util_10",
        "cpu_core_util_11",
        "cpu_core_util_12",
        "cpu_core_util_13",
        "cpu_core_util_14",
        "cpu_core_util_15",
        "cpu_core_util_16",
        "cpu_core_util_17",
        "cpu_core_util_18",
        "cpu_core_util_19",
        "cpu_core_util_20",
        "cpu_core_util_21",
        "cpu_core_util_22",
        "cpu_core_util_23",
        "cpu_core_util_24",
        "cpu_core_util_25",
        "cpu_core_util_26",
        "cpu_core_util_27",
        "cpu_core_util_28",
        "cpu_core_util_29",
        "cpu_core_util_30",
        "cpu_core_util_31",
        "cpu_core_util_32",
        "cpu_core_util_33",
        "cpu_core_util_34",
        "cpu_core_util_35",
        "cpu_core_util_36",
        "cpu_core_util_37",
        "cpu_core_util_38",
        "cpu_core_util_39",
        "cpu_core_util_40",
        "cpu_core_util_41",
        "cpu_core_util_42",
        "cpu_core_util_43",
        "cpu_core_util_44",
        "cpu_core_util_45",
        "cpu_core_util_46",
        "cpu_core_util_47",
        "cpu_core_util_48",
        "cpu_core_util_49",
        "cpu_core_util_50",
        "cpu_core_util_51",
        "cpu_core_util_52",
        "cpu_core_util_53",
        "cpu_core_util_54",
        "cpu_core_util_55",
        "cpu_core_util_56",
        "cpu_core_util_57",
        "cpu_core_util_58",
        "cpu_core_util_59",
        "cpu_core_util_60",
        "cpu_core_util_61",
        "cpu_core_util_62",
        "cpu_core_util_63",
        "cpu_core_util_64",
        "cpu_core_util_65",
        "cpu_core_util_66",
        "cpu_core_util_67",
        "cpu_core_util_68",
        "cpu_core_util_69",
        "cpu_core_util_70",
        "cpu_core_util_71",
        "cpu_core_util_72",
        "cpu_core_util_73",
        "cpu_core_util_74",
        "cpu_core_util_75",
        "cpu_core_util_76",
        "cpu_core_util_77",
        "cpu_core_util_78",
        "cpu_core_util_79",
        "cpu_core_util_80",
        "cpu_core_util_81",
        "cpu_core_util_82",
        "cpu_core_util_83",
        "cpu_core_util_84",
        "cpu_core_util_85",
        "cpu_core_util_86",
        "cpu_core_util_87",
        "cpu_core_util_88",
        "cpu_core_util_89",
        "cpu_core_util_90",
        "cpu_core_util_91",
        "cpu_core_util_92",
        "cpu_core_util_93",
        "cpu_core_util_94",
        "cpu_core_util_95",
        "cpu_core_util_96",
        "cpu_core_util_97",
        "cpu_core_util_98",
        "cpu_core_util_99",
        "cpu_core_util_100",
        "cpu_core_util_101",
        "cpu_core_util_102",
        "cpu_core_util_103",
        "cpu_core_util_104",
        "cpu_core_util_105",
        "cpu_core_util_106",
        "cpu_core_util_107",
        "cpu_core_util_108",
        "cpu_core_util_109",
        "cpu_core_util_110",
        "cpu_core_util_111",
        "cpu_core_util_112",
        "cpu_core_util_113",
        "cpu_core_util_114",
        "cpu_core_util_115",
        "cpu_core_util_116",
        "cpu_core_util_117",
        "cpu_core_util_118",
        "cpu_core_util_119",
        "cpu_core_util_120",
        "cpu_core_util_121",
        "cpu_core_util_122",
        "cpu_core_util_123",
        "cpu_core_util_124",
        "cpu_core_util_125",
        "cpu_core_util_126",
        "cpu_core_util_127",
    ],
    optional=[
        "cpu_core_util_2",
        "cpu_core_util_3",
        "cpu_core_util_4",
        "cpu_core_util_5",
        "cpu_core_util_6",
        "cpu_core_util_7",
        "cpu_core_util_8",
        "cpu_core_util_9",
        "cpu_core_util_10",
        "cpu_core_util_11",
        "cpu_core_util_12",
        "cpu_core_util_13",
        "cpu_core_util_14",
        "cpu_core_util_15",
        "cpu_core_util_16",
        "cpu_core_util_17",
        "cpu_core_util_18",
        "cpu_core_util_19",
        "cpu_core_util_20",
        "cpu_core_util_21",
        "cpu_core_util_22",
        "cpu_core_util_23",
        "cpu_core_util_24",
        "cpu_core_util_25",
        "cpu_core_util_26",
        "cpu_core_util_27",
        "cpu_core_util_28",
        "cpu_core_util_29",
        "cpu_core_util_30",
        "cpu_core_util_31",
        "cpu_core_util_32",
        "cpu_core_util_33",
        "cpu_core_util_34",
        "cpu_core_util_35",
        "cpu_core_util_36",
        "cpu_core_util_37",
        "cpu_core_util_38",
        "cpu_core_util_39",
        "cpu_core_util_40",
        "cpu_core_util_41",
        "cpu_core_util_42",
        "cpu_core_util_43",
        "cpu_core_util_44",
        "cpu_core_util_45",
        "cpu_core_util_46",
        "cpu_core_util_47",
        "cpu_core_util_48",
        "cpu_core_util_49",
        "cpu_core_util_50",
        "cpu_core_util_51",
        "cpu_core_util_52",
        "cpu_core_util_53",
        "cpu_core_util_54",
        "cpu_core_util_55",
        "cpu_core_util_56",
        "cpu_core_util_57",
        "cpu_core_util_58",
        "cpu_core_util_59",
        "cpu_core_util_60",
        "cpu_core_util_61",
        "cpu_core_util_62",
        "cpu_core_util_63",
        "cpu_core_util_64",
        "cpu_core_util_65",
        "cpu_core_util_66",
        "cpu_core_util_67",
        "cpu_core_util_68",
        "cpu_core_util_69",
        "cpu_core_util_70",
        "cpu_core_util_71",
        "cpu_core_util_72",
        "cpu_core_util_73",
        "cpu_core_util_74",
        "cpu_core_util_75",
        "cpu_core_util_76",
        "cpu_core_util_77",
        "cpu_core_util_78",
        "cpu_core_util_79",
        "cpu_core_util_80",
        "cpu_core_util_81",
        "cpu_core_util_82",
        "cpu_core_util_83",
        "cpu_core_util_84",
        "cpu_core_util_85",
        "cpu_core_util_86",
        "cpu_core_util_87",
        "cpu_core_util_88",
        "cpu_core_util_89",
        "cpu_core_util_90",
        "cpu_core_util_91",
        "cpu_core_util_92",
        "cpu_core_util_93",
        "cpu_core_util_94",
        "cpu_core_util_95",
        "cpu_core_util_96",
        "cpu_core_util_97",
        "cpu_core_util_98",
        "cpu_core_util_99",
        "cpu_core_util_100",
        "cpu_core_util_101",
        "cpu_core_util_102",
        "cpu_core_util_103",
        "cpu_core_util_104",
        "cpu_core_util_105",
        "cpu_core_util_106",
        "cpu_core_util_107",
        "cpu_core_util_108",
        "cpu_core_util_109",
        "cpu_core_util_110",
        "cpu_core_util_111",
        "cpu_core_util_112",
        "cpu_core_util_113",
        "cpu_core_util_114",
        "cpu_core_util_115",
        "cpu_core_util_116",
        "cpu_core_util_117",
        "cpu_core_util_118",
        "cpu_core_util_119",
        "cpu_core_util_120",
        "cpu_core_util_121",
        "cpu_core_util_122",
        "cpu_core_util_123",
        "cpu_core_util_124",
        "cpu_core_util_125",
        "cpu_core_util_126",
        "cpu_core_util_127",
    ],
)
