#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_oracle_ios_f_archive_log_backup_l_rb = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_l_rb",
    title=Title("Oracle archive log backup large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_ios_f_archive_log_backup_l_wb = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_l_wb",
    title=Title("Oracle archive log backup large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_archive_log_backup_s_rb = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_s_rb",
    title=Title("Oracle archive log backup small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_archive_log_backup_s_wb = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_s_wb",
    title=Title("Oracle archive log backup small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_RED,
)
metric_oracle_ios_f_archive_log_l_rb = metrics.Metric(
    name="oracle_ios_f_archive_log_l_rb",
    title=Title("Oracle archive log large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_archive_log_l_wb = metrics.Metric(
    name="oracle_ios_f_archive_log_l_wb",
    title=Title("Oracle archive log large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.RED,
)
metric_oracle_ios_f_archive_log_s_rb = metrics.Metric(
    name="oracle_ios_f_archive_log_s_rb",
    title=Title("Oracle archive log small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_archive_log_s_wb = metrics.Metric(
    name="oracle_ios_f_archive_log_s_wb",
    title=Title("Oracle archive log small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)
metric_oracle_ios_f_control_file_l_rb = metrics.Metric(
    name="oracle_ios_f_control_file_l_rb",
    title=Title("Oracle control file large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_control_file_l_wb = metrics.Metric(
    name="oracle_ios_f_control_file_l_wb",
    title=Title("Oracle control file large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_ORANGE,
)
metric_oracle_ios_f_control_file_s_rb = metrics.Metric(
    name="oracle_ios_f_control_file_s_rb",
    title=Title("Oracle control file small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_control_file_s_wb = metrics.Metric(
    name="oracle_ios_f_control_file_s_wb",
    title=Title("Oracle control file small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_ios_f_data_file_backup_l_rb = metrics.Metric(
    name="oracle_ios_f_data_file_backup_l_rb",
    title=Title("Oracle data file backup large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_data_file_backup_l_wb = metrics.Metric(
    name="oracle_ios_f_data_file_backup_l_wb",
    title=Title("Oracle data file backup large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_oracle_ios_f_data_file_backup_s_rb = metrics.Metric(
    name="oracle_ios_f_data_file_backup_s_rb",
    title=Title("Oracle data file backup small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_data_file_backup_s_wb = metrics.Metric(
    name="oracle_ios_f_data_file_backup_s_wb",
    title=Title("Oracle data file backup small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_data_file_copy_l_rb = metrics.Metric(
    name="oracle_ios_f_data_file_copy_l_rb",
    title=Title("Oracle data file copy large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_data_file_copy_l_wb = metrics.Metric(
    name="oracle_ios_f_data_file_copy_l_wb",
    title=Title("Oracle data file copy large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_oracle_ios_f_data_file_copy_s_rb = metrics.Metric(
    name="oracle_ios_f_data_file_copy_s_rb",
    title=Title("Oracle data file copy small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_data_file_copy_s_wb = metrics.Metric(
    name="oracle_ios_f_data_file_copy_s_wb",
    title=Title("Oracle data file copy small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_oracle_ios_f_data_file_incremental_backup_l_rb = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_l_rb",
    title=Title("Oracle data file incremental backup large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_data_file_incremental_backup_l_wb = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_l_wb",
    title=Title("Oracle data file incremental backup large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_data_file_incremental_backup_s_rb = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_s_rb",
    title=Title("Oracle data file incremental backup small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_data_file_incremental_backup_s_wb = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_s_wb",
    title=Title("Oracle data file incremental backup small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_ios_f_data_file_l_rb = metrics.Metric(
    name="oracle_ios_f_data_file_l_rb",
    title=Title("Oracle data file large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_oracle_ios_f_data_file_l_wb = metrics.Metric(
    name="oracle_ios_f_data_file_l_wb",
    title=Title("Oracle data file large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_data_file_s_rb = metrics.Metric(
    name="oracle_ios_f_data_file_s_rb",
    title=Title("Oracle data file small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_ios_f_data_file_s_wb = metrics.Metric(
    name="oracle_ios_f_data_file_s_wb",
    title=Title("Oracle data file small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_YELLOW,
)
metric_oracle_ios_f_data_pump_dump_file_l_rb = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_l_rb",
    title=Title("Oracle data pump dump file large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_ios_f_data_pump_dump_file_l_wb = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_l_wb",
    title=Title("Oracle data pump dump file large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_CYAN,
)
metric_oracle_ios_f_data_pump_dump_file_s_rb = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_s_rb",
    title=Title("Oracle data pump dump file small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_data_pump_dump_file_s_wb = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_s_wb",
    title=Title("Oracle data pump dump file small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_external_table_l_rb = metrics.Metric(
    name="oracle_ios_f_external_table_l_rb",
    title=Title("Oracle external table large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_external_table_l_wb = metrics.Metric(
    name="oracle_ios_f_external_table_l_wb",
    title=Title("Oracle external table large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_ios_f_external_table_s_rb = metrics.Metric(
    name="oracle_ios_f_external_table_s_rb",
    title=Title("Oracle external table small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_external_table_s_wb = metrics.Metric(
    name="oracle_ios_f_external_table_s_wb",
    title=Title("Oracle external table small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_flashback_log_l_rb = metrics.Metric(
    name="oracle_ios_f_flashback_log_l_rb",
    title=Title("Oracle flashback log large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_flashback_log_l_wb = metrics.Metric(
    name="oracle_ios_f_flashback_log_l_wb",
    title=Title("Oracle flashback log large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_flashback_log_s_rb = metrics.Metric(
    name="oracle_ios_f_flashback_log_s_rb",
    title=Title("Oracle flashback log small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_flashback_log_s_wb = metrics.Metric(
    name="oracle_ios_f_flashback_log_s_wb",
    title=Title("Oracle flashback log small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)
metric_oracle_ios_f_log_file_l_rb = metrics.Metric(
    name="oracle_ios_f_log_file_l_rb",
    title=Title("Oracle log file large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_log_file_l_wb = metrics.Metric(
    name="oracle_ios_f_log_file_l_wb",
    title=Title("Oracle log file large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_PINK,
)
metric_oracle_ios_f_log_file_s_rb = metrics.Metric(
    name="oracle_ios_f_log_file_s_rb",
    title=Title("Oracle log file small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_log_file_s_wb = metrics.Metric(
    name="oracle_ios_f_log_file_s_wb",
    title=Title("Oracle log file small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_PURPLE,
)
metric_oracle_ios_f_other_l_rb = metrics.Metric(
    name="oracle_ios_f_other_l_rb",
    title=Title("Oracle other large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_other_l_wb = metrics.Metric(
    name="oracle_ios_f_other_l_wb",
    title=Title("Oracle other large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_oracle_ios_f_other_s_rb = metrics.Metric(
    name="oracle_ios_f_other_s_rb",
    title=Title("Oracle other small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_other_s_wb = metrics.Metric(
    name="oracle_ios_f_other_s_wb",
    title=Title("Oracle other small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_ios_f_temp_file_l_rb = metrics.Metric(
    name="oracle_ios_f_temp_file_l_rb",
    title=Title("Oracle temp file large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_temp_file_l_wb = metrics.Metric(
    name="oracle_ios_f_temp_file_l_wb",
    title=Title("Oracle temp file large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_oracle_ios_f_temp_file_s_rb = metrics.Metric(
    name="oracle_ios_f_temp_file_s_rb",
    title=Title("Oracle temp file small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_temp_file_s_wb = metrics.Metric(
    name="oracle_ios_f_temp_file_s_wb",
    title=Title("Oracle temp file small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BROWN,
)

graph_oracle_iostat_bytes = graphs.Bidirectional(
    name="oracle_iostat_bytes",
    title=Title("Oracle IOSTAT bytes"),
    lower=graphs.Graph(
        name="oracle_iostat_wbytes",
        title=Title("Oracle IOSTAT write bytes"),
        simple_lines=[
            "oracle_ios_f_archive_log_s_wb",
            "oracle_ios_f_archive_log_l_wb",
            "oracle_ios_f_archive_log_backup_s_wb",
            "oracle_ios_f_archive_log_backup_l_wb",
            "oracle_ios_f_control_file_s_wb",
            "oracle_ios_f_control_file_l_wb",
            "oracle_ios_f_data_file_s_wb",
            "oracle_ios_f_data_file_l_wb",
            "oracle_ios_f_data_file_backup_s_wb",
            "oracle_ios_f_data_file_backup_l_wb",
            "oracle_ios_f_data_file_copy_s_wb",
            "oracle_ios_f_data_file_copy_l_wb",
            "oracle_ios_f_data_file_incremental_backup_s_wb",
            "oracle_ios_f_data_file_incremental_backup_l_wb",
            "oracle_ios_f_data_pump_dump_file_s_wb",
            "oracle_ios_f_data_pump_dump_file_l_wb",
            "oracle_ios_f_external_table_s_wb",
            "oracle_ios_f_external_table_l_wb",
            "oracle_ios_f_flashback_log_s_wb",
            "oracle_ios_f_flashback_log_l_wb",
            "oracle_ios_f_log_file_s_wb",
            "oracle_ios_f_log_file_l_wb",
            "oracle_ios_f_other_s_wb",
            "oracle_ios_f_other_l_wb",
            "oracle_ios_f_temp_file_s_wb",
            "oracle_ios_f_temp_file_l_wb",
        ],
    ),
    upper=graphs.Graph(
        name="oracle_iostat_rbytes",
        title=Title("Oracle IOSTAT read bytes"),
        simple_lines=[
            "oracle_ios_f_archive_log_s_rb",
            "oracle_ios_f_archive_log_l_rb",
            "oracle_ios_f_archive_log_backup_s_rb",
            "oracle_ios_f_archive_log_backup_l_rb",
            "oracle_ios_f_control_file_s_rb",
            "oracle_ios_f_control_file_l_rb",
            "oracle_ios_f_data_file_s_rb",
            "oracle_ios_f_data_file_l_rb",
            "oracle_ios_f_data_file_backup_s_rb",
            "oracle_ios_f_data_file_backup_l_rb",
            "oracle_ios_f_data_file_copy_s_rb",
            "oracle_ios_f_data_file_copy_l_rb",
            "oracle_ios_f_data_file_incremental_backup_s_rb",
            "oracle_ios_f_data_file_incremental_backup_l_rb",
            "oracle_ios_f_data_pump_dump_file_s_rb",
            "oracle_ios_f_data_pump_dump_file_l_rb",
            "oracle_ios_f_external_table_s_rb",
            "oracle_ios_f_external_table_l_rb",
            "oracle_ios_f_flashback_log_s_rb",
            "oracle_ios_f_flashback_log_l_rb",
            "oracle_ios_f_log_file_s_rb",
            "oracle_ios_f_log_file_l_rb",
            "oracle_ios_f_other_s_rb",
            "oracle_ios_f_other_l_rb",
            "oracle_ios_f_temp_file_s_rb",
            "oracle_ios_f_temp_file_l_rb",
        ],
    ),
)
