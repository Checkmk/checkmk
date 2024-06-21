#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_oracle_count = metrics.Metric(
    name="oracle_count",
    title=Title("Oracle count"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_oracle_buffer_busy_wait = metrics.Metric(
    name="oracle_buffer_busy_wait",
    title=Title("Oracle buffer busy wait"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_buffer_hit_ratio = metrics.Metric(
    name="oracle_buffer_hit_ratio",
    title=Title("Oracle buffer hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_oracle_consistent_gets = metrics.Metric(
    name="oracle_consistent_gets",
    title=Title("Oracle consistent gets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_db_block_change = metrics.Metric(
    name="oracle_db_block_change",
    title=Title("Oracle block change"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_db_block_gets = metrics.Metric(
    name="oracle_db_block_gets",
    title=Title("Oracle block gets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_oracle_db_cpu = metrics.Metric(
    name="oracle_db_cpu",
    title=Title("Oracle DB CPU time"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_oracle_db_time = metrics.Metric(
    name="oracle_db_time",
    title=Title("Oracle DB time"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_db_wait_time = metrics.Metric(
    name="oracle_db_wait_time",
    title=Title("Oracle DB non-idle wait"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_free_buffer_wait = metrics.Metric(
    name="oracle_free_buffer_wait",
    title=Title("Oracle free buffer wait"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_oracle_ios_f_archive_log_backup_l_r = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_l_r",
    title=Title("Oracle archive log backup large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_ios_f_archive_log_backup_l_rb = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_l_rb",
    title=Title("Oracle archive log backup large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_ios_f_archive_log_backup_l_w = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_l_w",
    title=Title("Oracle archive log backup large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_archive_log_backup_l_wb = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_l_wb",
    title=Title("Oracle archive log backup large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_archive_log_backup_s_r = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_s_r",
    title=Title("Oracle archive log backup small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_archive_log_backup_s_rb = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_s_rb",
    title=Title("Oracle archive log backup small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_archive_log_backup_s_w = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_s_w",
    title=Title("Oracle archive log backup small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_RED,
)
metric_oracle_ios_f_archive_log_backup_s_wb = metrics.Metric(
    name="oracle_ios_f_archive_log_backup_s_wb",
    title=Title("Oracle archive log backup small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_RED,
)
metric_oracle_ios_f_archive_log_l_r = metrics.Metric(
    name="oracle_ios_f_archive_log_l_r",
    title=Title("Oracle archive log large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_archive_log_l_rb = metrics.Metric(
    name="oracle_ios_f_archive_log_l_rb",
    title=Title("Oracle archive log large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_archive_log_l_w = metrics.Metric(
    name="oracle_ios_f_archive_log_l_w",
    title=Title("Oracle archive log large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)
metric_oracle_ios_f_archive_log_l_wb = metrics.Metric(
    name="oracle_ios_f_archive_log_l_wb",
    title=Title("Oracle archive log large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.RED,
)
metric_oracle_ios_f_archive_log_s_r = metrics.Metric(
    name="oracle_ios_f_archive_log_s_r",
    title=Title("Oracle archive log small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_archive_log_s_rb = metrics.Metric(
    name="oracle_ios_f_archive_log_s_rb",
    title=Title("Oracle archive log small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_archive_log_s_w = metrics.Metric(
    name="oracle_ios_f_archive_log_s_w",
    title=Title("Oracle archive log small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)
metric_oracle_ios_f_archive_log_s_wb = metrics.Metric(
    name="oracle_ios_f_archive_log_s_wb",
    title=Title("Oracle archive log small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)
metric_oracle_ios_f_control_file_l_r = metrics.Metric(
    name="oracle_ios_f_control_file_l_r",
    title=Title("Oracle control file large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_control_file_l_rb = metrics.Metric(
    name="oracle_ios_f_control_file_l_rb",
    title=Title("Oracle control file large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_control_file_l_w = metrics.Metric(
    name="oracle_ios_f_control_file_l_w",
    title=Title("Oracle control file large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_ORANGE,
)
metric_oracle_ios_f_control_file_l_wb = metrics.Metric(
    name="oracle_ios_f_control_file_l_wb",
    title=Title("Oracle control file large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_ORANGE,
)
metric_oracle_ios_f_control_file_s_r = metrics.Metric(
    name="oracle_ios_f_control_file_s_r",
    title=Title("Oracle control file small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_control_file_s_rb = metrics.Metric(
    name="oracle_ios_f_control_file_s_rb",
    title=Title("Oracle control file small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_control_file_s_w = metrics.Metric(
    name="oracle_ios_f_control_file_s_w",
    title=Title("Oracle control file small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_ios_f_control_file_s_wb = metrics.Metric(
    name="oracle_ios_f_control_file_s_wb",
    title=Title("Oracle control file small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_ios_f_data_file_backup_l_r = metrics.Metric(
    name="oracle_ios_f_data_file_backup_l_r",
    title=Title("Oracle data file backup large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_data_file_backup_l_rb = metrics.Metric(
    name="oracle_ios_f_data_file_backup_l_rb",
    title=Title("Oracle data file backup large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_data_file_backup_l_w = metrics.Metric(
    name="oracle_ios_f_data_file_backup_l_w",
    title=Title("Oracle data file backup large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_oracle_ios_f_data_file_backup_l_wb = metrics.Metric(
    name="oracle_ios_f_data_file_backup_l_wb",
    title=Title("Oracle data file backup large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_oracle_ios_f_data_file_backup_s_r = metrics.Metric(
    name="oracle_ios_f_data_file_backup_s_r",
    title=Title("Oracle data file backup small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_data_file_backup_s_rb = metrics.Metric(
    name="oracle_ios_f_data_file_backup_s_rb",
    title=Title("Oracle data file backup small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_data_file_backup_s_w = metrics.Metric(
    name="oracle_ios_f_data_file_backup_s_w",
    title=Title("Oracle data file backup small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_data_file_backup_s_wb = metrics.Metric(
    name="oracle_ios_f_data_file_backup_s_wb",
    title=Title("Oracle data file backup small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_data_file_copy_l_r = metrics.Metric(
    name="oracle_ios_f_data_file_copy_l_r",
    title=Title("Oracle data file copy large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_data_file_copy_l_rb = metrics.Metric(
    name="oracle_ios_f_data_file_copy_l_rb",
    title=Title("Oracle data file copy large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_data_file_copy_l_w = metrics.Metric(
    name="oracle_ios_f_data_file_copy_l_w",
    title=Title("Oracle data file copy large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_oracle_ios_f_data_file_copy_l_wb = metrics.Metric(
    name="oracle_ios_f_data_file_copy_l_wb",
    title=Title("Oracle data file copy large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_oracle_ios_f_data_file_copy_s_r = metrics.Metric(
    name="oracle_ios_f_data_file_copy_s_r",
    title=Title("Oracle data file copy small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_data_file_copy_s_rb = metrics.Metric(
    name="oracle_ios_f_data_file_copy_s_rb",
    title=Title("Oracle data file copy small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_data_file_copy_s_w = metrics.Metric(
    name="oracle_ios_f_data_file_copy_s_w",
    title=Title("Oracle data file copy small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_oracle_ios_f_data_file_copy_s_wb = metrics.Metric(
    name="oracle_ios_f_data_file_copy_s_wb",
    title=Title("Oracle data file copy small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_oracle_ios_f_data_file_incremental_backup_l_r = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_l_r",
    title=Title("Oracle data file incremental backup large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_data_file_incremental_backup_l_rb = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_l_rb",
    title=Title("Oracle data file incremental backup large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_data_file_incremental_backup_l_w = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_l_w",
    title=Title("Oracle data file incremental backup large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_data_file_incremental_backup_l_wb = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_l_wb",
    title=Title("Oracle data file incremental backup large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_data_file_incremental_backup_s_r = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_s_r",
    title=Title("Oracle data file incremental backup small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_data_file_incremental_backup_s_rb = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_s_rb",
    title=Title("Oracle data file incremental backup small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_data_file_incremental_backup_s_w = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_s_w",
    title=Title("Oracle data file incremental backup small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_ios_f_data_file_incremental_backup_s_wb = metrics.Metric(
    name="oracle_ios_f_data_file_incremental_backup_s_wb",
    title=Title("Oracle data file incremental backup small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_ios_f_data_file_l_r = metrics.Metric(
    name="oracle_ios_f_data_file_l_r",
    title=Title("Oracle data file large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_oracle_ios_f_data_file_l_rb = metrics.Metric(
    name="oracle_ios_f_data_file_l_rb",
    title=Title("Oracle data file large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_oracle_ios_f_data_file_l_w = metrics.Metric(
    name="oracle_ios_f_data_file_l_w",
    title=Title("Oracle data file large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_data_file_l_wb = metrics.Metric(
    name="oracle_ios_f_data_file_l_wb",
    title=Title("Oracle data file large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_data_file_s_r = metrics.Metric(
    name="oracle_ios_f_data_file_s_r",
    title=Title("Oracle data file small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_ios_f_data_file_s_rb = metrics.Metric(
    name="oracle_ios_f_data_file_s_rb",
    title=Title("Oracle data file small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_ios_f_data_file_s_w = metrics.Metric(
    name="oracle_ios_f_data_file_s_w",
    title=Title("Oracle data file small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_YELLOW,
)
metric_oracle_ios_f_data_file_s_wb = metrics.Metric(
    name="oracle_ios_f_data_file_s_wb",
    title=Title("Oracle data file small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_YELLOW,
)
metric_oracle_ios_f_data_pump_dump_file_l_r = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_l_r",
    title=Title("Oracle data pump dump file large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_ios_f_data_pump_dump_file_l_rb = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_l_rb",
    title=Title("Oracle data pump dump file large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_ios_f_data_pump_dump_file_l_w = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_l_w",
    title=Title("Oracle data pump dump file large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_CYAN,
)
metric_oracle_ios_f_data_pump_dump_file_l_wb = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_l_wb",
    title=Title("Oracle data pump dump file large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_CYAN,
)
metric_oracle_ios_f_data_pump_dump_file_s_r = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_s_r",
    title=Title("Oracle data pump dump file small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_data_pump_dump_file_s_rb = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_s_rb",
    title=Title("Oracle data pump dump file small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_data_pump_dump_file_s_w = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_s_w",
    title=Title("Oracle data pump dump file small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_data_pump_dump_file_s_wb = metrics.Metric(
    name="oracle_ios_f_data_pump_dump_file_s_wb",
    title=Title("Oracle data pump dump file small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_external_table_l_r = metrics.Metric(
    name="oracle_ios_f_external_table_l_r",
    title=Title("Oracle external table large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_external_table_l_rb = metrics.Metric(
    name="oracle_ios_f_external_table_l_rb",
    title=Title("Oracle external table large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_external_table_l_w = metrics.Metric(
    name="oracle_ios_f_external_table_l_w",
    title=Title("Oracle external table large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_ios_f_external_table_l_wb = metrics.Metric(
    name="oracle_ios_f_external_table_l_wb",
    title=Title("Oracle external table large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_ios_f_external_table_s_r = metrics.Metric(
    name="oracle_ios_f_external_table_s_r",
    title=Title("Oracle external table small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_external_table_s_rb = metrics.Metric(
    name="oracle_ios_f_external_table_s_rb",
    title=Title("Oracle external table small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_external_table_s_w = metrics.Metric(
    name="oracle_ios_f_external_table_s_w",
    title=Title("Oracle external table small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_external_table_s_wb = metrics.Metric(
    name="oracle_ios_f_external_table_s_wb",
    title=Title("Oracle external table small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_flashback_log_l_r = metrics.Metric(
    name="oracle_ios_f_flashback_log_l_r",
    title=Title("Oracle flashback log large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_flashback_log_l_rb = metrics.Metric(
    name="oracle_ios_f_flashback_log_l_rb",
    title=Title("Oracle flashback log large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_oracle_ios_f_flashback_log_l_w = metrics.Metric(
    name="oracle_ios_f_flashback_log_l_w",
    title=Title("Oracle flashback log large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_flashback_log_l_wb = metrics.Metric(
    name="oracle_ios_f_flashback_log_l_wb",
    title=Title("Oracle flashback log large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_flashback_log_s_r = metrics.Metric(
    name="oracle_ios_f_flashback_log_s_r",
    title=Title("Oracle flashback log small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_flashback_log_s_rb = metrics.Metric(
    name="oracle_ios_f_flashback_log_s_rb",
    title=Title("Oracle flashback log small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_oracle_ios_f_flashback_log_s_w = metrics.Metric(
    name="oracle_ios_f_flashback_log_s_w",
    title=Title("Oracle flashback log small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)
metric_oracle_ios_f_flashback_log_s_wb = metrics.Metric(
    name="oracle_ios_f_flashback_log_s_wb",
    title=Title("Oracle flashback log small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)
metric_oracle_ios_f_log_file_l_r = metrics.Metric(
    name="oracle_ios_f_log_file_l_r",
    title=Title("Oracle log file large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_log_file_l_rb = metrics.Metric(
    name="oracle_ios_f_log_file_l_rb",
    title=Title("Oracle log file large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_log_file_l_w = metrics.Metric(
    name="oracle_ios_f_log_file_l_w",
    title=Title("Oracle log file large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PINK,
)
metric_oracle_ios_f_log_file_l_wb = metrics.Metric(
    name="oracle_ios_f_log_file_l_wb",
    title=Title("Oracle log file large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_PINK,
)
metric_oracle_ios_f_log_file_s_r = metrics.Metric(
    name="oracle_ios_f_log_file_s_r",
    title=Title("Oracle log file small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_log_file_s_rb = metrics.Metric(
    name="oracle_ios_f_log_file_s_rb",
    title=Title("Oracle log file small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_ios_f_log_file_s_w = metrics.Metric(
    name="oracle_ios_f_log_file_s_w",
    title=Title("Oracle log file small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PURPLE,
)
metric_oracle_ios_f_log_file_s_wb = metrics.Metric(
    name="oracle_ios_f_log_file_s_wb",
    title=Title("Oracle log file small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_PURPLE,
)
metric_oracle_ios_f_other_l_r = metrics.Metric(
    name="oracle_ios_f_other_l_r",
    title=Title("Oracle other large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_other_l_rb = metrics.Metric(
    name="oracle_ios_f_other_l_rb",
    title=Title("Oracle other large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_other_l_w = metrics.Metric(
    name="oracle_ios_f_other_l_w",
    title=Title("Oracle other large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_oracle_ios_f_other_l_wb = metrics.Metric(
    name="oracle_ios_f_other_l_wb",
    title=Title("Oracle other large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_oracle_ios_f_other_s_r = metrics.Metric(
    name="oracle_ios_f_other_s_r",
    title=Title("Oracle other small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_other_s_rb = metrics.Metric(
    name="oracle_ios_f_other_s_rb",
    title=Title("Oracle other small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_ios_f_other_s_w = metrics.Metric(
    name="oracle_ios_f_other_s_w",
    title=Title("Oracle other small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_ios_f_other_s_wb = metrics.Metric(
    name="oracle_ios_f_other_s_wb",
    title=Title("Oracle other small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_ios_f_temp_file_l_r = metrics.Metric(
    name="oracle_ios_f_temp_file_l_r",
    title=Title("Oracle temp file large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_temp_file_l_rb = metrics.Metric(
    name="oracle_ios_f_temp_file_l_rb",
    title=Title("Oracle temp file large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_ios_f_temp_file_l_w = metrics.Metric(
    name="oracle_ios_f_temp_file_l_w",
    title=Title("Oracle temp file large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_oracle_ios_f_temp_file_l_wb = metrics.Metric(
    name="oracle_ios_f_temp_file_l_wb",
    title=Title("Oracle temp file large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_oracle_ios_f_temp_file_s_r = metrics.Metric(
    name="oracle_ios_f_temp_file_s_r",
    title=Title("Oracle temp file small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_temp_file_s_rb = metrics.Metric(
    name="oracle_ios_f_temp_file_s_rb",
    title=Title("Oracle temp file small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_ios_f_temp_file_s_w = metrics.Metric(
    name="oracle_ios_f_temp_file_s_w",
    title=Title("Oracle temp file small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BROWN,
)
metric_oracle_ios_f_temp_file_s_wb = metrics.Metric(
    name="oracle_ios_f_temp_file_s_wb",
    title=Title("Oracle temp file small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BROWN,
)
metric_oracle_ios_f_total_l_r = metrics.Metric(
    name="oracle_ios_f_total_l_r",
    title=Title("Oracle total large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_ios_f_total_l_rb = metrics.Metric(
    name="oracle_ios_f_total_l_rb",
    title=Title("Oracle total large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_ios_f_total_l_w = metrics.Metric(
    name="oracle_ios_f_total_l_w",
    title=Title("Oracle total large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_ios_f_total_l_wb = metrics.Metric(
    name="oracle_ios_f_total_l_wb",
    title=Title("Oracle total large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_ios_f_total_s_r = metrics.Metric(
    name="oracle_ios_f_total_s_r",
    title=Title("Oracle total small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_total_s_rb = metrics.Metric(
    name="oracle_ios_f_total_s_rb",
    title=Title("Oracle total small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_total_s_w = metrics.Metric(
    name="oracle_ios_f_total_s_w",
    title=Title("Oracle total small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_total_s_wb = metrics.Metric(
    name="oracle_ios_f_total_s_wb",
    title=Title("Oracle total small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_library_cache_hit_ratio = metrics.Metric(
    name="oracle_library_cache_hit_ratio",
    title=Title("Oracle library cache hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_oracle_number_of_nodes_not_in_target_state = metrics.Metric(
    name="oracle_number_of_nodes_not_in_target_state",
    title=Title("Oracle number of nodes in target state"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_oracle_pga_total_freeable_pga_memory = metrics.Metric(
    name="oracle_pga_total_freeable_pga_memory",
    title=Title("Oracle total freeable PGA memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_oracle_pga_total_pga_allocated = metrics.Metric(
    name="oracle_pga_total_pga_allocated",
    title=Title("Oracle total PGA allocated"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_oracle_pga_total_pga_inuse = metrics.Metric(
    name="oracle_pga_total_pga_inuse",
    title=Title("Oracle total PGA inuse"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_oracle_physical_reads = metrics.Metric(
    name="oracle_physical_reads",
    title=Title("Oracle physical reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_physical_writes = metrics.Metric(
    name="oracle_physical_writes",
    title=Title("Oracle physical writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_pin_hits_sum = metrics.Metric(
    name="oracle_pin_hits_sum",
    title=Title("Oracle pin hits sum"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_oracle_pins_sum = metrics.Metric(
    name="oracle_pins_sum",
    title=Title("Oracle pins sum"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_sga_buffer_cache = metrics.Metric(
    name="oracle_sga_buffer_cache",
    title=Title("Oracle buffer cache size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_oracle_sga_java_pool = metrics.Metric(
    name="oracle_sga_java_pool",
    title=Title("Oracle Java pool size"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_oracle_sga_large_pool = metrics.Metric(
    name="oracle_sga_large_pool",
    title=Title("Oracle large pool size"),
    unit=UNIT_BYTES,
    color=metrics.Color.PINK,
)
metric_oracle_sga_redo_buffer = metrics.Metric(
    name="oracle_sga_redo_buffer",
    title=Title("Oracle redo buffers"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_oracle_sga_shared_io_pool = metrics.Metric(
    name="oracle_sga_shared_io_pool",
    title=Title("Oracle shared IO pool size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GREEN,
)
metric_oracle_sga_shared_pool = metrics.Metric(
    name="oracle_sga_shared_pool",
    title=Title("Oracle shared pool size"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_GREEN,
)
metric_oracle_sga_size = metrics.Metric(
    name="oracle_sga_size",
    title=Title("Oracle maximum SGA size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BROWN,
)
metric_oracle_sga_streams_pool = metrics.Metric(
    name="oracle_sga_streams_pool",
    title=Title("Oracle streams pool size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BROWN,
)
metric_oracle_wait_class_administrative_waited = metrics.Metric(
    name="oracle_wait_class_administrative_waited",
    title=Title("Oracle administrative wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)
metric_oracle_wait_class_administrative_waited_fg = metrics.Metric(
    name="oracle_wait_class_administrative_waited_fg",
    title=Title("Oracle administrative wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_RED,
)
metric_oracle_wait_class_application_waited = metrics.Metric(
    name="oracle_wait_class_application_waited",
    title=Title("Oracle application wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_RED,
)
metric_oracle_wait_class_application_waited_fg = metrics.Metric(
    name="oracle_wait_class_application_waited_fg",
    title=Title("Oracle application wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_RED,
)
metric_oracle_wait_class_cluster_waited = metrics.Metric(
    name="oracle_wait_class_cluster_waited",
    title=Title("Oracle cluster wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_wait_class_cluster_waited_fg = metrics.Metric(
    name="oracle_wait_class_cluster_waited_fg",
    title=Title("Oracle cluster wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_oracle_wait_class_commit_waited = metrics.Metric(
    name="oracle_wait_class_commit_waited",
    title=Title("Oracle commit wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_wait_class_commit_waited_fg = metrics.Metric(
    name="oracle_wait_class_commit_waited_fg",
    title=Title("Oracle commit wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_oracle_wait_class_concurrency_waited = metrics.Metric(
    name="oracle_wait_class_concurrency_waited",
    title=Title("Oracle concurrency wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_oracle_wait_class_concurrency_waited_fg = metrics.Metric(
    name="oracle_wait_class_concurrency_waited_fg",
    title=Title("Oracle concurrency wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_oracle_wait_class_configuration_waited = metrics.Metric(
    name="oracle_wait_class_configuration_waited",
    title=Title("Oracle configuration wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_oracle_wait_class_configuration_waited_fg = metrics.Metric(
    name="oracle_wait_class_configuration_waited_fg",
    title=Title("Oracle configuration wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_oracle_wait_class_idle_waited = metrics.Metric(
    name="oracle_wait_class_idle_waited",
    title=Title("Oracle idle wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_wait_class_idle_waited_fg = metrics.Metric(
    name="oracle_wait_class_idle_waited_fg",
    title=Title("Oracle idle wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_oracle_wait_class_network_waited = metrics.Metric(
    name="oracle_wait_class_network_waited",
    title=Title("Oracle network wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_wait_class_network_waited_fg = metrics.Metric(
    name="oracle_wait_class_network_waited_fg",
    title=Title("Oracle network wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_wait_class_other_waited = metrics.Metric(
    name="oracle_wait_class_other_waited",
    title=Title("Oracle other wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_wait_class_other_waited_fg = metrics.Metric(
    name="oracle_wait_class_other_waited_fg",
    title=Title("Oracle other wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_oracle_wait_class_scheduler_waited = metrics.Metric(
    name="oracle_wait_class_scheduler_waited",
    title=Title("Oracle scheduler wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_wait_class_scheduler_waited_fg = metrics.Metric(
    name="oracle_wait_class_scheduler_waited_fg",
    title=Title("Oracle scheduler wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_oracle_wait_class_system_io_waited = metrics.Metric(
    name="oracle_wait_class_system_io_waited",
    title=Title("Oracle system I/O wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_wait_class_system_io_waited_fg = metrics.Metric(
    name="oracle_wait_class_system_io_waited_fg",
    title=Title("Oracle system I/O wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_oracle_wait_class_total = metrics.Metric(
    name="oracle_wait_class_total",
    title=Title("Oracle total waited"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLACK,
)
metric_oracle_wait_class_total_fg = metrics.Metric(
    name="oracle_wait_class_total_fg",
    title=Title("Oracle total waited (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLACK,
)
metric_oracle_wait_class_user_io_waited = metrics.Metric(
    name="oracle_wait_class_user_io_waited",
    title=Title("Oracle user I/O wait class"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_oracle_wait_class_user_io_waited_fg = metrics.Metric(
    name="oracle_wait_class_user_io_waited_fg",
    title=Title("Oracle user I/O wait class (FG)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)


perfometer_oracle_hit_ratio = perfometers.Stacked(
    name="oracle_hit_ratio",
    lower=perfometers.Perfometer(
        name="oracle_library_cache_hit_ratio",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["oracle_library_cache_hit_ratio"],
    ),
    upper=perfometers.Perfometer(
        name="oracle_buffer_hit_ratio",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100.0),
        ),
        segments=["oracle_buffer_hit_ratio"],
    ),
)
perfometer_oracle_ios_f_total_s_l_1 = perfometers.Bidirectional(
    name="oracle_ios_f_total_s_l_1",
    left=perfometers.Perfometer(
        name="oracle_ios_f_total_rb",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=[
            "oracle_ios_f_total_s_rb",
            "oracle_ios_f_total_l_rb",
        ],
    ),
    right=perfometers.Perfometer(
        name="oracle_ios_f_total_wb",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=[
            "oracle_ios_f_total_s_wb",
            "oracle_ios_f_total_l_wb",
        ],
    ),
)
perfometer_oracle_count = perfometers.Perfometer(
    name="oracle_count",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(500),
    ),
    segments=["oracle_count"],
)
perfometer_oracle_wait_class_total = perfometers.Bidirectional(
    name="oracle_wait_class_total",
    left=perfometers.Perfometer(
        name="oracle_wait_class_total",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=["oracle_wait_class_total"],
    ),
    right=perfometers.Perfometer(
        name="oracle_wait_class_total_fg",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=["oracle_wait_class_total_fg"],
    ),
)
perfometer_oracle_sga_pga_size = perfometers.Perfometer(
    name="oracle_sga_pga_size",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(30000000000),
    ),
    segments=[
        "oracle_sga_size",
        "oracle_pga_total_pga_allocated",
    ],
)
perfometer_oracle_db_cpu_wait_time = perfometers.Perfometer(
    name="oracle_db_cpu_wait_time",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(
            metrics.Constant(
                Title(""),
                UNIT_COUNTER,
                metrics.Color.BLUE,
                50.0,
            )
        ),
    ),
    segments=[
        "oracle_db_cpu",
        "oracle_db_wait_time",
    ],
)
perfometer_oracle_ios_f_total_s_l_2 = perfometers.Bidirectional(
    name="oracle_ios_f_total_s_l_2",
    left=perfometers.Perfometer(
        name="oracle_ios_f_total_s_r",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=[
            "oracle_ios_f_total_s_r",
            "oracle_ios_f_total_l_r",
        ],
    ),
    right=perfometers.Perfometer(
        name="oracle_ios_f_total_s_w",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=[
            "oracle_ios_f_total_s_w",
            "oracle_ios_f_total_l_w",
        ],
    ),
)

graph_oracle_buffer_pool_statistics = graphs.Graph(
    name="oracle_buffer_pool_statistics",
    title=Title("Oracle buffer pool statistics"),
    simple_lines=[
        "oracle_db_block_gets",
        "oracle_db_block_change",
        "oracle_consistent_gets",
        "oracle_free_buffer_wait",
        "oracle_buffer_busy_wait",
    ],
)
graph_oracle_db_time_statistics = graphs.Graph(
    name="oracle_db_time_statistics",
    title=Title("Oracle DB time statistics"),
    compound_lines=[
        "oracle_db_cpu",
        "oracle_db_wait_time",
    ],
    simple_lines=["oracle_db_time"],
    optional=["oracle_db_wait_time"],
)
graph_oracle_hit_ratio = graphs.Bidirectional(
    name="oracle_hit_ratio",
    title=Title("Oracle hit ratio"),
    lower=graphs.Graph(
        name="oracle_hit_ratio",
        title=Title("Oracle library cache hit ratio"),
        compound_lines=["oracle_library_cache_hit_ratio"],
    ),
    upper=graphs.Graph(
        name="oracle_hit_ratio",
        title=Title("Oracle buffer hit ratio"),
        compound_lines=["oracle_buffer_hit_ratio"],
    ),
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
graph_oracle_iostat_total_bytes = graphs.Bidirectional(
    name="oracle_iostat_total_bytes",
    title=Title("Oracle IOSTAT total bytes"),
    lower=graphs.Graph(
        name="oracle_iostat_total_wbytes",
        title=Title("Oracle IOSTAT total writes bytes"),
        simple_lines=[
            "oracle_ios_f_total_s_wb",
            "oracle_ios_f_total_l_wb",
        ],
    ),
    upper=graphs.Graph(
        name="oracle_iostat_total_rbytes",
        title=Title("Oracle IOSTAT total read bytes"),
        simple_lines=[
            "oracle_ios_f_total_s_rb",
            "oracle_ios_f_total_l_rb",
        ],
    ),
)
graph_oracle_iostat_total_ios = graphs.Bidirectional(
    name="oracle_iostat_total_ios",
    title=Title("Oracle IOSTAT total IOs"),
    lower=graphs.Graph(
        name="oracle_iostat_total_ios_w",
        title=Title("Oracle IOSTAT total IO writes"),
        simple_lines=[
            "oracle_ios_f_total_s_w",
            "oracle_ios_f_total_l_w",
        ],
    ),
    upper=graphs.Graph(
        name="oracle_iostat_total_ios_r",
        title=Title("Oracle IOSTAT total IO reads"),
        simple_lines=[
            "oracle_ios_f_total_s_r",
            "oracle_ios_f_total_l_r",
        ],
    ),
)
graph_oracle_library_cache_statistics = graphs.Graph(
    name="oracle_library_cache_statistics",
    title=Title("Oracle library cache statistics"),
    simple_lines=[
        "oracle_pins_sum",
        "oracle_pin_hits_sum",
    ],
)
graph_oracle_pga_memory_info = graphs.Graph(
    name="oracle_pga_memory_info",
    title=Title("Oracle PGA memory statistics"),
    simple_lines=[
        "oracle_pga_total_pga_allocated",
        "oracle_pga_total_pga_inuse",
        "oracle_pga_total_freeable_pga_memory",
    ],
    optional=["oracle_pga_total_freeable_pga_memory"],
)
graph_oracle_physical_io_oracle_physical_io = graphs.Bidirectional(
    name="oracle_physical_io",
    title=Title("Oracle physical IO"),
    lower=graphs.Graph(
        name="oracle_physical_writes",
        title=Title("Oracle physical IO"),
        compound_lines=["oracle_physical_writes"],
    ),
    upper=graphs.Graph(
        name="oracle_physical_reads",
        title=Title("Oracle physical IO reads"),
        compound_lines=["oracle_physical_reads"],
    ),
)
graph_oracle_sga_info = graphs.Graph(
    name="oracle_sga_info",
    title=Title("Oracle SGA memory statistics"),
    compound_lines=[
        "oracle_sga_buffer_cache",
        "oracle_sga_shared_pool",
        "oracle_sga_shared_io_pool",
        "oracle_sga_redo_buffer",
        "oracle_sga_java_pool",
        "oracle_sga_large_pool",
        "oracle_sga_streams_pool",
    ],
    simple_lines=["oracle_sga_size"],
    optional=[
        "oracle_sga_java_pool",
        "oracle_sga_large_pool",
        "oracle_sga_streams_pool",
    ],
)
graph_oracle_sga_pga_total = graphs.Graph(
    name="oracle_sga_pga_total",
    title=Title("Oracle memory"),
    compound_lines=[
        "oracle_sga_size",
        "oracle_pga_total_pga_allocated",
    ],
    simple_lines=[
        metrics.Sum(
            Title("Oracle total Memory"),
            metrics.Color.GRAY,
            [
                "oracle_sga_size",
                "oracle_pga_total_pga_allocated",
            ],
        )
    ],
)
graph_oracle_wait_class = graphs.Bidirectional(
    name="oracle_wait_class",
    title=Title("Oracle Wait Class (FG lines are downside)"),
    lower=graphs.Graph(
        name="oracle_wait_class_fg",
        title=Title("Oracle wait class"),
        simple_lines=[
            "oracle_wait_class_total_fg",
            "oracle_wait_class_administrative_waited_fg",
            "oracle_wait_class_application_waited_fg",
            "oracle_wait_class_cluster_waited_fg",
            "oracle_wait_class_commit_waited_fg",
            "oracle_wait_class_concurrency_waited_fg",
            "oracle_wait_class_configuration_waited_fg",
            "oracle_wait_class_idle_waited_fg",
            "oracle_wait_class_network_waited_fg",
            "oracle_wait_class_other_waited_fg",
            "oracle_wait_class_scheduler_waited_fg",
            "oracle_wait_class_system_io_waited_fg",
            "oracle_wait_class_user_io_waited_fg",
        ],
        optional=[
            "oracle_wait_class_administrative_waited_fg",
            "oracle_wait_class_application_waited_fg",
            "oracle_wait_class_cluster_waited_fg",
            "oracle_wait_class_commit_waited_fg",
            "oracle_wait_class_concurrency_waited_fg",
            "oracle_wait_class_configuration_waited_fg",
            "oracle_wait_class_idle_waited_fg",
            "oracle_wait_class_network_waited_fg",
            "oracle_wait_class_other_waited_fg",
            "oracle_wait_class_scheduler_waited_fg",
            "oracle_wait_class_system_io_waited_fg",
            "oracle_wait_class_user_io_waited_fg",
        ],
    ),
    upper=graphs.Graph(
        name="oracle_wait_class_waited",
        title=Title("Oracle wait class"),
        simple_lines=[
            "oracle_wait_class_total",
            "oracle_wait_class_administrative_waited",
            "oracle_wait_class_application_waited",
            "oracle_wait_class_cluster_waited",
            "oracle_wait_class_commit_waited",
            "oracle_wait_class_concurrency_waited",
            "oracle_wait_class_configuration_waited",
            "oracle_wait_class_idle_waited",
            "oracle_wait_class_network_waited",
            "oracle_wait_class_other_waited",
            "oracle_wait_class_scheduler_waited",
            "oracle_wait_class_system_io_waited",
            "oracle_wait_class_user_io_waited",
        ],
        optional=[
            "oracle_wait_class_administrative_waited",
            "oracle_wait_class_application_waited",
            "oracle_wait_class_cluster_waited",
            "oracle_wait_class_commit_waited",
            "oracle_wait_class_concurrency_waited",
            "oracle_wait_class_configuration_waited",
            "oracle_wait_class_idle_waited",
            "oracle_wait_class_network_waited",
            "oracle_wait_class_other_waited",
            "oracle_wait_class_scheduler_waited",
            "oracle_wait_class_system_io_waited",
            "oracle_wait_class_user_io_waited",
        ],
    ),
)
