#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    AgeNotation,
    Node,
    NumberField,
    SINotation,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_AGE = Unit(AgeNotation())
UNIT_BYTES = Unit(SINotation("B"))

node_software_applications_oracle = Node(
    name="software_applications_oracle",
    path=["software", "applications", "oracle"],
    title=Title("Oracle DB"),
)

node_software_applications_oracle_dataguard_stats = Node(
    name="software_applications_oracle_dataguard_stats",
    path=["software", "applications", "oracle", "dataguard_stats"],
    title=Title("Oracle dataguard statistics"),
    table=Table(
        view=View(name="invoradataguardstats", title=Title("Oracle dataguard statistics")),
        columns={
            "sid": TextField(Title("SID")),
            "db_unique": TextField(Title("Name")),
            "role": TextField(Title("Role")),
            "switchover": TextField(Title("Switchover")),
        },
    ),
)

node_software_applications_oracle_instance = Node(
    name="software_applications_oracle_instance",
    path=["software", "applications", "oracle", "instance"],
    title=Title("Oracle instances"),
    table=Table(
        view=View(name="invorainstance", title=Title("Oracle instances")),
        columns={
            "sid": TextField(Title("SID")),
            "pname": TextField(Title("Process name")),
            "version": TextField(Title("Version")),
            "openmode": TextField(Title("Open mode")),
            "logmode": TextField(Title("Log mode")),
            "logins": TextField(Title("Logins")),
            "db_uptime": NumberField(Title("Uptime"), render=UNIT_AGE),
            "db_creation_time": TextField(Title("Creation time")),
        },
    ),
)

node_software_applications_oracle_pga = Node(
    name="software_applications_oracle_pga",
    path=["software", "applications", "oracle", "pga"],
    title=Title("Oracle PGA info"),
    table=Table(
        view=View(name="invorapga", title=Title("Oracle PGA info")),
        columns={
            "sid": TextField(Title("SID")),
            "aggregate_pga_auto_target": NumberField(
                Title("Aggregate PGA auto target"), render=UNIT_BYTES
            ),
            "aggregate_pga_target_parameter": NumberField(
                Title("Aggregate PGA target parameter"), render=UNIT_BYTES
            ),
            "bytes_processed": NumberField(Title("Bytes processed"), render=UNIT_BYTES),
            "extra_bytes_read_written": NumberField(
                Title("Extra bytes read/written"), render=UNIT_BYTES
            ),
            "global_memory_bound": NumberField(Title("Global memory bound"), render=UNIT_BYTES),
            "maximum_pga_allocated": NumberField(Title("Maximum PGA allocated"), render=UNIT_BYTES),
            "maximum_pga_used_for_auto_workareas": NumberField(
                Title("Maximum PGA used for auto workareas"), render=UNIT_BYTES
            ),
            "maximum_pga_used_for_manual_workareas": NumberField(
                Title("Maximum PGA used for manual workareas"), render=UNIT_BYTES
            ),
            "total_pga_allocated": NumberField(Title("Total PGA allocated"), render=UNIT_BYTES),
            "total_pga_inuse": NumberField(Title("Total PGA inuse"), render=UNIT_BYTES),
            "total_pga_used_for_auto_workareas": NumberField(
                Title("Total PGA used for auto workareas"), render=UNIT_BYTES
            ),
            "total_pga_used_for_manual_workareas": NumberField(
                Title("Total PGA used for manual workareas"), render=UNIT_BYTES
            ),
            "total_freeable_pga_memory": NumberField(
                Title("Total freeable PGA memory"), render=UNIT_BYTES
            ),
        },
    ),
)

node_software_applications_oracle_recovery_area = Node(
    name="software_applications_oracle_recovery_area",
    path=["software", "applications", "oracle", "recovery_area"],
    title=Title("Oracle recovery areas"),
    table=Table(
        view=View(name="invorarecoveryarea", title=Title("Oracle recovery areas")),
        columns={
            "sid": TextField(Title("SID")),
            "flashback": TextField(Title("Flashback")),
        },
    ),
)

node_software_applications_oracle_sga = Node(
    name="software_applications_oracle_sga",
    path=["software", "applications", "oracle", "sga"],
    title=Title("Oracle SGA info"),
    table=Table(
        view=View(name="invorasga", title=Title("Oracle SGA info")),
        columns={
            "sid": TextField(Title("SID")),
            "fixed_size": NumberField(Title("Fixed size"), render=UNIT_BYTES),
            "redo_buffer": NumberField(Title("Redo buffers"), render=UNIT_BYTES),
            "buf_cache_size": NumberField(Title("Buffer cache size"), render=UNIT_BYTES),
            "in_mem_area_size": NumberField(Title("In-memory area"), render=UNIT_BYTES),
            "shared_pool_size": NumberField(Title("Shared pool size"), render=UNIT_BYTES),
            "large_pool_size": NumberField(Title("Large pool size"), render=UNIT_BYTES),
            "java_pool_size": NumberField(Title("Java pool size"), render=UNIT_BYTES),
            "streams_pool_size": NumberField(Title("Streams pool size"), render=UNIT_BYTES),
            "shared_io_pool_size": NumberField(Title("Shared pool size"), render=UNIT_BYTES),
            "data_trans_cache_size": NumberField(
                Title("Data transfer cache size"), render=UNIT_BYTES
            ),
            "granule_size": NumberField(Title("Granule size"), render=UNIT_BYTES),
            "max_size": NumberField(Title("Maximum size"), render=UNIT_BYTES),
            "start_oh_shared_pool": NumberField(
                Title("Startup overhead in shared pool"), render=UNIT_BYTES
            ),
            "free_mem_avail": NumberField(Title("Free SGA memory available"), render=UNIT_BYTES),
        },
    ),
)

node_software_applications_oracle_systemparameter = Node(
    name="software_applications_oracle_systemparameter",
    path=["software", "applications", "oracle", "systemparameter"],
    title=Title("Oracle system parameters"),
    table=Table(
        view=View(name="invorasystemparameter", title=Title("Oracle system parameters")),
        columns={
            "sid": TextField(Title("SID")),
            "name": TextField(Title("Name")),
            "value": TextField(Title("Value")),
            "isdefault": TextField(Title("Is default")),
        },
    ),
)

node_software_applications_oracle_tablespaces = Node(
    name="software_applications_oracle_tablespaces",
    path=["software", "applications", "oracle", "tablespaces"],
    title=Title("Oracle tablespaces"),
    table=Table(
        view=View(name="invoratablespace", title=Title("Oracle tablespaces")),
        columns={
            "sid": TextField(Title("SID")),
            "name": TextField(Title("Name")),
            "version": TextField(Title("Version")),
            "type": TextField(Title("Type")),
            "autoextensible": TextField(Title("Autoextensible")),
            "current_size": NumberField(Title("Current size"), render=UNIT_BYTES),
            "max_size": NumberField(Title("Max. size"), render=UNIT_BYTES),
            "used_size": NumberField(Title("Used size"), render=UNIT_BYTES),
            "num_increments": TextField(Title("#Increments")),
            "increment_size": NumberField(Title("Increment size"), render=UNIT_BYTES),
            "free_space": NumberField(Title("Free space"), render=UNIT_BYTES),
        },
    ),
)
