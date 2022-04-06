#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

import cmk.gui.sites as sites
from cmk.gui.globals import active_config


def load_mkeventd_rules():
    rule_packs = ec.load_rule_packs()

    # TODO: We should really separate the rule stats from this "config load logic"
    rule_stats = _get_rule_stats_from_ec()

    for rule_pack in rule_packs:
        pack_hits = 0
        for rule in rule_pack["rules"]:
            hits = rule_stats.get(rule["id"], 0)
            rule["hits"] = hits
            pack_hits += hits
        rule_pack["hits"] = pack_hits

    return rule_packs


def _get_rule_stats_from_ec() -> Dict[str, int]:
    # Add information about rule hits: If we are running on OMD then we know
    # the path to the state retention file of mkeventd and can read the rule
    # statistics directly from that file.
    rule_stats: Dict[str, int] = {}
    for rule_id, count in sites.live().query("GET eventconsolerules\nColumns: rule_id rule_hits\n"):
        rule_stats.setdefault(rule_id, 0)
        rule_stats[rule_id] += count
    return rule_stats


def save_mkeventd_rules(rule_packs):
    ec.save_rule_packs(rule_packs, active_config.mkeventd_pprint_rules)


def export_mkp_rule_pack(rule_pack):
    ec.export_rule_pack(rule_pack, active_config.mkeventd_pprint_rules)
