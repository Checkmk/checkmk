#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import graph_info, metric_info

# .
#   .--Metrics-------------------------------------------------------------.
#   |                   __  __      _        _                             |
#   |                  |  \/  | ___| |_ _ __(_) ___ ___                    |
#   |                  | |\/| |/ _ \ __| '__| |/ __/ __|                   |
#   |                  | |  | |  __/ |_| |  | | (__\__ \                   |
#   |                  |_|  |_|\___|\__|_|  |_|\___|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definitions of metrics                                              |
#   '----------------------------------------------------------------------'

# Title are always lower case - except the first character!
# Colors: See indexed_color() in cmk/gui/plugins/metrics/utils.py

metric_info["fc_rx_bytes"] = {
    "title": _("Input"),
    "unit": "bytes/s",
    "color": "31/a",
}

metric_info["fc_tx_bytes"] = {
    "title": _("Output"),
    "unit": "bytes/s",
    "color": "35/a",
}

metric_info["fc_rx_frames"] = {
    "title": _("Received Frames"),
    "unit": "1/s",
    "color": "31/b",
}

metric_info["fc_tx_frames"] = {
    "title": _("Transmitted Frames"),
    "unit": "1/s",
    "color": "35/b",
}

metric_info["fc_rx_words"] = {
    "title": _("Received Words"),
    "unit": "1/s",
    "color": "26/b",
}

metric_info["fc_tx_words"] = {
    "title": _("Transmitted Words"),
    "unit": "1/s",
    "color": "31/b",
}

metric_info["fc_crc_errors"] = {
    "title": _("Receive CRC errors"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["fc_encouts"] = {
    "title": _("Enc-Outs"),
    "unit": "1/s",
    "color": "12/a",
}

metric_info["fc_encins"] = {
    "title": _("Enc-Ins"),
    "unit": "1/s",
    "color": "13/b",
}

metric_info["fc_bbcredit_zero"] = {
    "title": _("BBcredit zero"),
    "unit": "1/s",
    "color": "46/a",
}

metric_info["fc_c3discards"] = {
    "title": _("C3 discards"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["fc_notxcredits"] = {
    "title": _("No TX Credits"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["fc_c2c3_discards"] = {
    "title": _("C2 and c3 discards"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["fc_link_fails"] = {
    "title": _("Link failures"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["fc_sync_losses"] = {
    "title": _("Sync losses"),
    "unit": "1/s",
    "color": "12/a",
}

metric_info["fc_prim_seq_errors"] = {
    "title": _("Primitive sequence errors"),
    "unit": "1/s",
    "color": "13/a",
}

metric_info["fc_invalid_tx_words"] = {
    "title": _("Invalid TX words"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["fc_invalid_crcs"] = {
    "title": _("Invalid CRCs"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["fc_address_id_errors"] = {
    "title": _("Address ID errors"),
    "unit": "1/s",
    "color": "16/a",
}

metric_info["fc_link_resets_in"] = {
    "title": _("Link resets in"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["fc_link_resets_out"] = {
    "title": _("Link resets out"),
    "unit": "1/s",
    "color": "22/a",
}

metric_info["fc_offline_seqs_in"] = {
    "title": _("Offline sequences in"),
    "unit": "1/s",
    "color": "23/a",
}

metric_info["fc_offline_seqs_out"] = {
    "title": _("Offline sequences out"),
    "unit": "1/s",
    "color": "24/a",
}

metric_info["fc_c2_fbsy_frames"] = {
    "title": _("F_BSY frames"),
    "unit": "1/s",
    "color": "25/a",
}

metric_info["fc_c2_frjt_frames"] = {
    "title": _("F_RJT frames"),
    "unit": "1/s",
    "color": "26/a",
}

# .
#   .--Graphs--------------------------------------------------------------.
#   |                    ____                 _                            |
#   |                   / ___|_ __ __ _ _ __ | |__  ___                    |
#   |                  | |  _| '__/ _` | '_ \| '_ \/ __|                   |
#   |                  | |_| | | | (_| | |_) | | | \__ \                   |
#   |                   \____|_|  \__,_| .__/|_| |_|___/                   |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |  Definitions of time series graphs                                   |
#   '----------------------------------------------------------------------'

graph_info["fc_errors"] = {
    "title": _("Errors"),
    "metrics": [
        ("fc_crc_errors", "area"),
        ("fc_c3discards", "stack"),
        ("fc_notxcredits", "stack"),
        ("fc_encouts", "stack"),
        ("fc_encins", "stack"),
        ("fc_bbcredit_zero", "stack"),
    ],
    "optional_metrics": [
        "fc_encins",
        "fc_bbcredit_zero",
    ],
}

graph_info["fc_errors_detailed"] = {
    "title": _("Errors"),
    "metrics": [
        ("fc_link_fails", "stack"),
        ("fc_sync_losses", "stack"),
        ("fc_prim_seq_errors", "stack"),
        ("fc_invalid_tx_words", "stack"),
        ("fc_invalid_crcs", "stack"),
        ("fc_address_id_errors", "stack"),
        ("fc_link_resets_in", "stack"),
        ("fc_link_resets_out", "stack"),
        ("fc_offline_seqs_in", "stack"),
        ("fc_offline_seqs_out", "stack"),
        ("fc_c2c3_discards", "stack"),
        ("fc_c2_fbsy_frames", "stack"),
        ("fc_c2_frjt_frames", "stack"),
    ],
}

graph_info["throughput"] = {
    "title": _("Throughput"),
    "metrics": [
        ("fc_tx_bytes", "-area"),
        ("fc_rx_bytes", "area"),
    ],
}

graph_info["frames"] = {
    "title": _("Frames"),
    "metrics": [
        ("fc_tx_frames", "-area"),
        ("fc_rx_frames", "area"),
    ],
}

graph_info["words"] = {
    "title": _("Words"),
    "metrics": [
        ("fc_tx_words", "-area"),
        ("fc_rx_words", "area"),
    ],
}
