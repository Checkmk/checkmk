#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_oracle_ios_f_archive_log_s_w = metrics.Metric(
    name="oracle_ios_f_archive_log_s_w",
    title=Title("Oracle archive log small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)
metric_oracle_ios_f_archive_log_l_w = metrics.Metric(
    name="oracle_ios_f_archive_log_l_w",
    title=Title("Oracle archive log large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)
metric_oracle_ios_f_archive_log_backup_s_w = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_s_w",
    title=Title("Oracle archive log backup small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_RED,
)
metric_oracle_ios_f_archive_log_backup_l_w = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_l_w",
    title=Title("Oracle archive log backup large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_control_file_s_w = metrics.Metric(
    name="oracle_ios_f_control_file_s_w",
    title=Title("Oracle control file small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_ios_f_control_file_l_w = metrics.Metric(
    name="oracle_ios_f_control_file_l_w",
    title=Title("Oracle control file large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_ORANGE,
)
metric_oracle_ios_f_data_file_s_w = metrics.Metric(
    name="oracle_ios_f_data_file_s_w",
    title=Title("Oracle data file small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_YELLOW,
)
metric_oracle_ios_f_data_file_l_w = metrics.Metric(
    name="oracle_ios_f_data_file_l_w",
    title=Title("Oracle data file large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_data_file_backup_s_w = metrics.Metric(
    name="oracle_ios_f_data_file_backup_s_w",
    title=Title("Oracle data file backup small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_data_file_backup_l_w = metrics.Metric(
    name="oracle_ios_f_data_file_backup_l_w",
    title=Title("Oracle data file backup large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_oracle_ios_f_data_file_copy_s_w = metrics.Metric(
    name="oracle_ios_f_data_file_copy_s_w",
    title=Title("Oracle data file copy small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_oracle_ios_f_data_file_copy_l_w = metrics.Metric(
    name="oracle_ios_f_data_file_copy_l_w",
    title=Title("Oracle data file copy large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_oracle_ios_f_data_file_incremental_backup_s_w = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_s_w",
    title=Title("Oracle data file incremental backup small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_ios_f_data_file_incremental_backup_l_w = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_l_w",
    title=Title("Oracle data file incremental backup large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_data_pump_dump_file_s_w = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_s_w",
    title=Title("Oracle data pump dump file small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_data_pump_dump_file_l_w = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_l_w",
    title=Title("Oracle data pump dump file large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_CYAN,
)
metric_oracle_ios_f_external_table_s_w = metrics.Metric(
    name="oracle_ios_f_external_table_s_w",
    title=Title("Oracle external table small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_external_table_l_w = metrics.Metric(
    name="oracle_ios_f_external_table_l_w",
    title=Title("Oracle external table large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_ios_f_flashback_log_s_w = metrics.Metric(
    name="oracle_ios_f_flashback_log_s_w",
    title=Title("Oracle flashback log small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)
metric_oracle_ios_f_flashback_log_l_w = metrics.Metric(
    name="oracle_ios_f_flashback_log_l_w",
    title=Title("Oracle flashback log large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_log_file_s_w = metrics.Metric(
    name="oracle_ios_f_log_file_s_w",
    title=Title("Oracle log file small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PURPLE,
)
metric_oracle_ios_f_log_file_l_w = metrics.Metric(
    name="oracle_ios_f_log_file_l_w",
    title=Title("Oracle log file large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PINK,
)
metric_oracle_ios_f_other_s_w = metrics.Metric(
    name="oracle_ios_f_other_s_w",
    title=Title("Oracle other small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_ios_f_other_l_w = metrics.Metric(
    name="oracle_ios_f_other_l_w",
    title=Title("Oracle other large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_oracle_ios_f_temp_file_s_w = metrics.Metric(
    name="oracle_ios_f_temp_file_s_w",
    title=Title("Oracle temp file small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BROWN,
)
metric_oracle_ios_f_temp_file_l_w = metrics.Metric(
    name="oracle_ios_f_temp_file_l_w",
    title=Title("Oracle temp file large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_oracle_ios_f_archive_log_s_r = metrics.Metric(
    name="oracle_ios_f_archive_log_s_r",
    title=Title("Oracle archive log small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_archive_log_l_r = metrics.Metric(
    name="oracle_ios_f_archive_log_l_r",
    title=Title("Oracle archive log large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_archive_log_backup_s_r = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_s_r",
    title=Title("Oracle archive log backup small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_archive_log_backup_l_r = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_l_r",
    title=Title("Oracle archive log backup large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_ios_f_control_file_s_r = metrics.Metric(
    name="oracle_ios_f_control_file_s_r",
    title=Title("Oracle control file small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_control_file_l_r = metrics.Metric(
    name="oracle_ios_f_control_file_l_r",
    title=Title("Oracle control file large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_data_file_s_r = metrics.Metric(
    name="oracle_ios_f_data_file_s_r",
    title=Title("Oracle data file small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_ios_f_data_file_l_r = metrics.Metric(
    name="oracle_ios_f_data_file_l_r",
    title=Title("Oracle data file large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_oracle_ios_f_data_file_backup_s_r = metrics.Metric(
    name="oracle_ios_f_data_file_backup_s_r",
    title=Title("Oracle data file backup small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_data_file_backup_l_r = metrics.Metric(
    name="oracle_ios_f_data_file_backup_l_r",
    title=Title("Oracle data file backup large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_data_file_copy_s_r = metrics.Metric(
    name="oracle_ios_f_data_file_copy_s_r",
    title=Title("Oracle data file copy small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_data_file_copy_l_r = metrics.Metric(
    name="oracle_ios_f_data_file_copy_l_r",
    title=Title("Oracle data file copy large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_data_file_incremental_backup_s_r = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_s_r",
    title=Title("Oracle data file incremental backup small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_data_file_incremental_backup_l_r = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_l_r",
    title=Title("Oracle data file incremental backup large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_data_pump_dump_file_s_r = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_s_r",
    title=Title("Oracle data pump dump file small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_data_pump_dump_file_l_r = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_l_r",
    title=Title("Oracle data pump dump file large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_ios_f_external_table_s_r = metrics.Metric(
    name="oracle_ios_f_external_table_s_r",
    title=Title("Oracle external table small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_external_table_l_r = metrics.Metric(
    name="oracle_ios_f_external_table_l_r",
    title=Title("Oracle external table large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_flashback_log_s_r = metrics.Metric(
    name="oracle_ios_f_flashback_log_s_r",
    title=Title("Oracle flashback log small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_flashback_log_l_r = metrics.Metric(
    name="oracle_ios_f_flashback_log_l_r",
    title=Title("Oracle flashback log large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_log_file_s_r = metrics.Metric(
    name="oracle_ios_f_log_file_s_r",
    title=Title("Oracle log file small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_log_file_l_r = metrics.Metric(
    name="oracle_ios_f_log_file_l_r",
    title=Title("Oracle log file large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_other_s_r = metrics.Metric(
    name="oracle_ios_f_other_s_r",
    title=Title("Oracle other small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_other_l_r = metrics.Metric(
    name="oracle_ios_f_other_l_r",
    title=Title("Oracle other large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_temp_file_s_r = metrics.Metric(
    name="oracle_ios_f_temp_file_s_r",
    title=Title("Oracle temp file small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_temp_file_l_r = metrics.Metric(
    name="oracle_ios_f_temp_file_l_r",
    title=Title("Oracle temp file large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)

graph_oracle_iostat_ios = graphs.Bidirectional(
    name="oracle_iostat_ios",
    title=Title("Oracle IOSTAT IO"),
    lower=graphs.Graph(
        name="oracle_iostat_ios_w",
        title=Title("Oracle IOSTAT IO writes"),
        simple_lines=[
            "oracle_ios_f_archive_log_s_w",
            "oracle_ios_f_archive_log_l_w",
            "oracle_ios_f_archive_log_backup_s_w",
            "oracle_ios_f_archive_log_backup_l_w",
            "oracle_ios_f_control_file_s_w",
            "oracle_ios_f_control_file_l_w",
            "oracle_ios_f_data_file_s_w",
            "oracle_ios_f_data_file_l_w",
            "oracle_ios_f_data_file_backup_s_w",
            "oracle_ios_f_data_file_backup_l_w",
            "oracle_ios_f_data_file_copy_s_w",
            "oracle_ios_f_data_file_copy_l_w",
            "oracle_ios_f_data_file_incremental_backup_s_w",
            "oracle_ios_f_data_file_incremental_backup_l_w",
            "oracle_ios_f_data_pump_dump_file_s_w",
            "oracle_ios_f_data_pump_dump_file_l_w",
            "oracle_ios_f_external_table_s_w",
            "oracle_ios_f_external_table_l_w",
            "oracle_ios_f_flashback_log_s_w",
            "oracle_ios_f_flashback_log_l_w",
            "oracle_ios_f_log_file_s_w",
            "oracle_ios_f_log_file_l_w",
            "oracle_ios_f_other_s_w",
            "oracle_ios_f_other_l_w",
            "oracle_ios_f_temp_file_s_w",
            "oracle_ios_f_temp_file_l_w",
        ],
    ),
    upper=graphs.Graph(
        name="oracle_iostat_ios_r",
        title=Title("Oracle IOSTAT IO reads"),
        simple_lines=[
            "oracle_ios_f_archive_log_s_r",
            "oracle_ios_f_archive_log_l_r",
            "oracle_ios_f_archive_log_backup_s_r",
            "oracle_ios_f_archive_log_backup_l_r",
            "oracle_ios_f_control_file_s_r",
            "oracle_ios_f_control_file_l_r",
            "oracle_ios_f_data_file_s_r",
            "oracle_ios_f_data_file_l_r",
            "oracle_ios_f_data_file_backup_s_r",
            "oracle_ios_f_data_file_backup_l_r",
            "oracle_ios_f_data_file_copy_s_r",
            "oracle_ios_f_data_file_copy_l_r",
            "oracle_ios_f_data_file_incremental_backup_s_r",
            "oracle_ios_f_data_file_incremental_backup_l_r",
            "oracle_ios_f_data_pump_dump_file_s_r",
            "oracle_ios_f_data_pump_dump_file_l_r",
            "oracle_ios_f_external_table_s_r",
            "oracle_ios_f_external_table_l_r",
            "oracle_ios_f_flashback_log_s_r",
            "oracle_ios_f_flashback_log_l_r",
            "oracle_ios_f_log_file_s_r",
            "oracle_ios_f_log_file_l_r",
            "oracle_ios_f_other_s_r",
            "oracle_ios_f_other_l_r",
            "oracle_ios_f_temp_file_s_r",
            "oracle_ios_f_temp_file_l_r",
        ],
    ),
)
