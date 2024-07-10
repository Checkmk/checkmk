#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_fc_link_fails = metrics.Metric(
    name="fc_link_fails",
    title=Title("Link failures"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)
metric_fc_sync_losses = metrics.Metric(
    name="fc_sync_losses",
    title=Title("Sync losses"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_fc_prim_seq_errors = metrics.Metric(
    name="fc_prim_seq_errors",
    title=Title("Primitive sequence errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_fc_invalid_tx_words = metrics.Metric(
    name="fc_invalid_tx_words",
    title=Title("Invalid TX words"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_fc_invalid_crcs = metrics.Metric(
    name="fc_invalid_crcs",
    title=Title("Invalid CRCs"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_fc_address_id_errors = metrics.Metric(
    name="fc_address_id_errors",
    title=Title("Address ID errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_fc_link_resets_in = metrics.Metric(
    name="fc_link_resets_in",
    title=Title("Link resets in"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)
metric_fc_link_resets_out = metrics.Metric(
    name="fc_link_resets_out",
    title=Title("Link resets out"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_fc_offline_seqs_in = metrics.Metric(
    name="fc_offline_seqs_in",
    title=Title("Offline sequences in"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_fc_offline_seqs_out = metrics.Metric(
    name="fc_offline_seqs_out",
    title=Title("Offline sequences out"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BROWN,
)
metric_fc_c2c3_discards = metrics.Metric(
    name="fc_c2c3_discards",
    title=Title("C2 and c3 discards"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GRAY,
)
metric_fc_c2_fbsy_frames = metrics.Metric(
    name="fc_c2_fbsy_frames",
    title=Title("F_BSY frames"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_fc_c2_frjt_frames = metrics.Metric(
    name="fc_c2_frjt_frames",
    title=Title("F_RJT frames"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)

graph_fc_errors_detailed = graphs.Graph(
    name="fc_errors_detailed",
    title=Title("Errors"),
    compound_lines=[
        "fc_link_fails",
        "fc_sync_losses",
        "fc_prim_seq_errors",
        "fc_invalid_tx_words",
        "fc_invalid_crcs",
        "fc_address_id_errors",
        "fc_link_resets_in",
        "fc_link_resets_out",
        "fc_offline_seqs_in",
        "fc_offline_seqs_out",
        "fc_c2c3_discards",
        "fc_c2_fbsy_frames",
        "fc_c2_frjt_frames",
    ],
)
