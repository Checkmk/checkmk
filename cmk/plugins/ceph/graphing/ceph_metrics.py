#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title
from cmk.plugins.ceph.constants import PG_METRICS_MAP

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_num_pgs = metrics.Metric(
    name="num_pgs",
    title=Title("Number of Placement Groups"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BROWN,
)
metric_pgstate_activating_undersized = metrics.Metric(
    name="pgstate_activating_undersized",
    title=Title("PGs Activating + Undersized"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_pgstate_activating_undersized_degraded = metrics.Metric(
    name="pgstate_activating_undersized_degraded",
    title=Title("PGs Activating + Undersized + Degradedpgstate"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_pgstate_active_clean = metrics.Metric(
    name="pgstate_active_clean",
    title=Title("PGs Active + Clean"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_CYAN,
)
metric_pgstate_active_clean_inconsistent = metrics.Metric(
    name="pgstate_active_clean_inconsistent",
    title=Title("PGs Active + Clean + Inconsistent"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_pgstate_active_clean_remapped = metrics.Metric(
    name="pgstate_active_clean_remapped",
    title=Title("PGs Active + Clean + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PINK,
)
metric_pgstate_active_clean_scrubbing = metrics.Metric(
    name="pgstate_active_clean_scrubbing",
    title=Title("PGs Active + Clean + Scrubbing"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pgstate_active_clean_scrubbing_deep = metrics.Metric(
    name="pgstate_active_clean_scrubbing_deep",
    title=Title("PGs Active + Clean + Scrubbing + Deep"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_pgstate_active_clean_scrubbing_deep_repair = metrics.Metric(
    name="pgstate_active_clean_scrubbing_deep_repair",
    title=Title("PGs Active + Clean + Scrubbing + Deep + Repair"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_BLUE,
)
metric_pgstate_active_clean_scrubbing_deep_snaptrim_wait = metrics.Metric(
    name="pgstate_active_clean_scrubbing_deep_snaptrim_wait",
    title=Title("PGs Active + Clean + Scrubbing + Deep + Snaptrim + Wait"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_pgstate_active_clean_snaptrim = metrics.Metric(
    name="pgstate_active_clean_snaptrim",
    title=Title("PGs Active + Clean + Snaptrim"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_pgstate_active_clean_snaptrim_wait = metrics.Metric(
    name="pgstate_active_clean_snaptrim_wait",
    title=Title("PGs Active + Clean + Snaptrim + Wait"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_pgstate_active_clean_wait = metrics.Metric(
    name="pgstate_active_clean_wait",
    title=Title("PGs Active + Clean + Wait"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_pgstate_active_degraded = metrics.Metric(
    name="pgstate_active_degraded",
    title=Title("PGs Active + Degraded"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_pgstate_active_recovering = metrics.Metric(
    name="pgstate_active_recovering",
    title=Title("PGs Active + Recovering"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pgstate_active_recovering_degraded = metrics.Metric(
    name="pgstate_active_recovering_degraded",
    title=Title("PGs Active + Recovering + Degraded"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_pgstate_active_recovering_degraded_inconsistent = metrics.Metric(
    name="pgstate_active_recovering_degraded_inconsistent",
    title=Title("PGs Active + Recovering + Degraded + Inconsistent"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_pgstate_active_recovering_degraded_remapped = metrics.Metric(
    name="pgstate_active_recovering_degraded_remapped",
    title=Title("PGs Active + Recovering + Degraded + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_pgstate_active_recovering_remapped = metrics.Metric(
    name="pgstate_active_recovering_remapped",
    title=Title("PGs Active + Recovering + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_pgstate_active_recovering_undersized = metrics.Metric(
    name="pgstate_active_recovering_undersized",
    title=Title("PGs Active + Recovering + Undersized"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_pgstate_active_recovering_undersized_degraded_remapped = metrics.Metric(
    name="pgstate_active_recovering_undersized_degraded_remapped",
    title=Title("PGs Active + Recovering + Undersized + Degraded + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_pgstate_active_recovering_undersized_remapped = metrics.Metric(
    name="pgstate_active_recovering_undersized_remapped",
    title=Title("PGs Active + Recovering + Undersized + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_pgstate_active_recovery_wait = metrics.Metric(
    name="pgstate_active_recovery_wait",
    title=Title("PGs Active + Recovery + Wait"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pgstate_active_recovery_wait_degraded = metrics.Metric(
    name="pgstate_active_recovery_wait_degraded",
    title=Title("PGs Active + Recovery + Wait + Degraded"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_pgstate_active_recovery_wait_degraded_inconsistent = metrics.Metric(
    name="pgstate_active_recovery_wait_degraded_inconsistent",
    title=Title("PGs Active + Recovery + Wait + Degraded + Inconsistent"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_pgstate_active_recovery_wait_degraded_remapped = metrics.Metric(
    name="pgstate_active_recovery_wait_degraded_remapped",
    title=Title("PGs Active + Recovery + Wait + Degraded + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_pgstate_active_recovery_wait_remapped = metrics.Metric(
    name="pgstate_active_recovery_wait_remapped",
    title=Title("PGs Active + Recovery + Wait + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_pgstate_active_recovery_wait_undersized_degraded = metrics.Metric(
    name="pgstate_active_recovery_wait_undersized_degraded",
    title=Title("PGs Active + Recovery + Wait + Undersized + Degraded"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_pgstate_active_recovery_wait_undersized_degraded_remapped = metrics.Metric(
    name="pgstate_active_recovery_wait_undersized_degraded_remapped",
    title=Title("PGs Active + Recovery + Wait + Undersized + Degraded + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_pgstate_active_recovery_wait_undersized_remapped = metrics.Metric(
    name="pgstate_active_recovery_wait_undersized_remapped",
    title=Title("PGs Active + Recovery + Wait + Undersized + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PINK,
)
metric_pgstate_active_remapped = metrics.Metric(
    name="pgstate_active_remapped",
    title=Title("PGs Active + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pgstate_active_remapped_backfill_toofull = metrics.Metric(
    name="pgstate_active_remapped_backfill_toofull",
    title=Title("PGs Active + Remapped + Backfill + Toofull"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_BLUE,
)
metric_pgstate_active_remapped_backfill_wait = metrics.Metric(
    name="pgstate_active_remapped_backfill_wait",
    title=Title("PGs Active + Remapped + Backfill + Wait"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_pgstate_active_remapped_backfill_wait_backfill_toofull = metrics.Metric(
    name="pgstate_active_remapped_backfill_wait_backfill_toofull",
    title=Title("PGs Active + Remapped + Backfill + Wait + Backfill + Toofull"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_pgstate_active_remapped_backfilling = metrics.Metric(
    name="pgstate_active_remapped_backfilling",
    title=Title("PGs Active + Remapped + Backfilling"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_pgstate_active_remapped_inconsistent_backfill_toofull = metrics.Metric(
    name="pgstate_active_remapped_inconsistent_backfill_toofull",
    title=Title("PGs Active + Remapped + Inconsistent + Backfill + Toofull"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_pgstate_active_remapped_inconsistent_backfill_wait = metrics.Metric(
    name="pgstate_active_remapped_inconsistent_backfill_wait",
    title=Title("PGs Active + Remapped + Inconsistent + Backfill + Wait"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_pgstate_active_remapped_inconsistent_backfilling = metrics.Metric(
    name="pgstate_active_remapped_inconsistent_backfilling",
    title=Title("PGs Active + Remapped + Inconsistent + Backfilling"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_pgstate_active_undersized = metrics.Metric(
    name="pgstate_active_undersized",
    title=Title("PGs Active + Undersized"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pgstate_active_undersized_degraded = metrics.Metric(
    name="pgstate_active_undersized_degraded",
    title=Title("PGs Active + Undersized + Degraded"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_pgstate_active_undersized_degraded_inconsistent = metrics.Metric(
    name="pgstate_active_undersized_degraded_inconsistent",
    title=Title("PGs Active + Undersized + Degraded + Inconsistent"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_pgstate_active_undersized_degraded_remapped_backfill_toofull = metrics.Metric(
    name="pgstate_active_undersized_degraded_remapped_backfill_toofull",
    title=Title("PGs Active + Undersized + Degraded + Remapped + Backfill + Toofull"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_pgstate_active_undersized_degraded_remapped_backfill_wait = metrics.Metric(
    name="pgstate_active_undersized_degraded_remapped_backfill_wait",
    title=Title("PGs Active + Undersized + Degraded + Remapped + Backfill + Wait"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_pgstate_active_undersized_degraded_remapped_backfilling = metrics.Metric(
    name="pgstate_active_undersized_degraded_remapped_backfilling",
    title=Title("PGs Active + Undersized + Degraded + Remapped + Backfilling"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_pgstate_active_undersized_degraded_remapped_inconsistent_backfill_toofull = metrics.Metric(
    name="pgstate_active_undersized_degraded_remapped_inconsistent_backfill_toofull",
    title=Title(
        "PGs Active + Undersized + Degraded + Remapped + Inconsistent + Backfill + Toofull"
    ),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_pgstate_active_undersized_degraded_remapped_inconsistent_backfill_wait = metrics.Metric(
    name="pgstate_active_undersized_degraded_remapped_inconsistent_backfill_wait",
    title=Title("PGs Active + Undersized + Degraded + Remapped + Inconsistent + Backfill + Wait"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pgstate_active_undersized_degraded_remapped_inconsistent_backfilling = metrics.Metric(
    name="pgstate_active_undersized_degraded_remapped_inconsistent_backfilling",
    title=Title("PGs Active + Undersized + Degraded + Remapped + Inconsistent + Backfilling"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_pgstate_active_undersized_remapped = metrics.Metric(
    name="pgstate_active_undersized_remapped",
    title=Title("PGs Active + Undersized + Remapped"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_pgstate_active_undersized_remapped_backfill_toofull = metrics.Metric(
    name="pgstate_active_undersized_remapped_backfill_toofull",
    title=Title("PGs Active + Undersized + Remapped + Backfill + Toofull"),
    unit=UNIT_COUNTER,
    color=metrics.Color.RED,
)
metric_pgstate_active_undersized_remapped_backfill_wait = metrics.Metric(
    name="pgstate_active_undersized_remapped_backfill_wait",
    title=Title("PGs Active + Undersized + Remapped + Backfill + Wait"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_pgstate_active_undersized_remapped_backfilling = metrics.Metric(
    name="pgstate_active_undersized_remapped_backfilling",
    title=Title("PGs Active + Undersized + Remapped + Backfilling"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_pgstate_down = metrics.Metric(
    name="pgstate_down",
    title=Title("PGs Down"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_pgstate_incomplete = metrics.Metric(
    name="pgstate_incomplete",
    title=Title("PGs Incomplete"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pgstate_peering = metrics.Metric(
    name="pgstate_peering",
    title=Title("PGs Peering"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_pgstate_remapped_peering = metrics.Metric(
    name="pgstate_remapped_peering",
    title=Title("PGs Remapped + Peering"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_pgstate_stale_active_undersized = metrics.Metric(
    name="pgstate_stale_active_undersized",
    title=Title("PGs Stale+active + Undersized"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_RED,
)
metric_pgstate_stale_active_clean = metrics.Metric(
    name="pgstate_stale_active_clean",
    title=Title("PGs Stale + Active + Clean"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GRAY,
)
metric_pgstate_stale_active_undersized_degraded = metrics.Metric(
    name="pgstate_stale_active_undersized_degraded",
    title=Title("PGs Stale + Active + Undersized + Degraded"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_GREEN,
)
metric_pgstate_stale_undersized_degraded_peered = metrics.Metric(
    name="pgstate_stale_undersized_degraded_peered",
    title=Title("PGs Stale + Undersized + Degraded + Peered"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_pgstate_stale_undersized_peered = metrics.Metric(
    name="pgstate_stale_undersized_peered",
    title=Title("PGs Stale + Undersized + Peered"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pgstate_undersized_degraded_peered = metrics.Metric(
    name="pgstate_undersized_degraded_peered",
    title=Title("PGs Undersized + Degraded + Peered"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PURPLE,
)
metric_pgstate_undersized_peered = metrics.Metric(
    name="pgstate_undersized_peered",
    title=Title("PGs Undersized + Peered"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_CYAN,
)
metric_pgstate_unknown = metrics.Metric(
    name="pgstate_unknown",
    title=Title("PGs Unknown"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_GRAY,
)
graph_pgs = graphs.Graph(
    name="pgs",
    title=Title("Placement groups"),
    minimal_range=graphs.MinimalRange(
        0,
        metrics.MaximumOf("num_pgs", metrics.Color.GRAY),
    ),
    # TODO split into multiple graphs
    compound_lines=(all_metrics := [f"pgstate_{m}" for m in PG_METRICS_MAP.values()]),
    simple_lines=["num_pgs"],
    optional=all_metrics,
)
