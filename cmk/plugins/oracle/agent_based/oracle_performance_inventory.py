#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import InventoryPlugin, InventoryResult, TableRow
from cmk.plugins.lib.oracle import SectionPerformance


def inventory_oracle_performance(section: SectionPerformance) -> InventoryResult:
    for entry, entryinfo in section.items():
        if "SGA_info" in entryinfo:
            sga_data = entryinfo["SGA_info"]
            yield TableRow(
                path=["software", "applications", "oracle", "sga"],
                key_columns={
                    "sid": entry,
                },
                inventory_columns={},
                status_columns={
                    "fixed_size": sga_data.get("Fixed SGA Size"),
                    "max_size": sga_data.get("Maximum SGA Size"),
                    "redo_buffer": sga_data.get("Redo Buffers"),
                    "buf_cache_size": sga_data.get("Buffer Cache Size"),
                    "in_mem_area_size": sga_data.get("In-Memory Area Size"),
                    "shared_pool_size": sga_data.get("Shared Pool Size"),
                    "large_pool_size": sga_data.get("Large Pool Size"),
                    "java_pool_size": sga_data.get("Java Pool Size"),
                    "streams_pool_size": sga_data.get("Streams Pool Size"),
                    "shared_io_pool_size": sga_data.get("Shared IO Pool Size"),
                    "data_trans_cache_size": sga_data.get("Data Transfer Cache Size"),
                    "granule_size": sga_data.get("Granule Size"),
                    "start_oh_shared_pool": sga_data.get("Startup overhead in Shared Pool"),
                    "free_mem_avail": sga_data.get("Free SGA Memory Available"),
                },
            )

        if "PGA_info" in entryinfo:
            # entryinfo["PGA_info"] = Dict[str, List[int, str]]
            pga_data = {key: entrylist[0] for key, entrylist in entryinfo["PGA_info"].items()}
            yield TableRow(
                path=["software", "applications", "oracle", "pga"],
                key_columns={
                    "sid": entry,
                },
                inventory_columns={},
                status_columns={
                    "aggregate_pga_auto_target": pga_data.get("aggregate PGA auto target"),
                    "aggregate_pga_target_parameter": pga_data.get(
                        "aggregate PGA target parameter"
                    ),
                    "bytes_processed": pga_data.get("bytes processed"),
                    "extra_bytes_read_written": pga_data.get("extra bytes read/written"),
                    "global_memory_bound": pga_data.get("global memory bound"),
                    "maximum_pga_allocated": pga_data.get("maximum PGA allocated"),
                    "maximum_pga_used_for_auto_workareas": pga_data.get(
                        "maximum PGA used for auto workareas"
                    ),
                    "maximum_pga_used_for_manual_workareas": pga_data.get(
                        "maximum PGA used for manual workareas"
                    ),
                    "total_pga_allocated": pga_data.get("total PGA allocated"),
                    "total_pga_inuse": pga_data.get("total PGA inuse"),
                    "total_pga_used_for_auto_workareas": pga_data.get(
                        "total PGA used for auto workareas"
                    ),
                    "total_pga_used_for_manual_workareas": pga_data.get(
                        "total PGA used for manual workareas"
                    ),
                    "total_freeable_pga_memory": pga_data.get("total freeable PGA memory"),
                },
            )


inventory_plugin_oracle_performance = InventoryPlugin(
    name="oracle_performance",
    inventory_function=inventory_oracle_performance,
)
