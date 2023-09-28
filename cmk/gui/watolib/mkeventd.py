#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

import cmk.gui.sites as sites
from cmk.gui.config import active_config


def get_rule_stats_from_ec() -> Mapping[str, int]:
    # Add information about rule hits: If we are running on OMD then we know
    # the path to the state retention file of mkeventd and can read the rule
    # statistics directly from that file.
    rule_stats: dict[str, int] = {}
    for rule_id, count in sites.live().query("GET eventconsolerules\nColumns: rule_id rule_hits\n"):
        rule_stats.setdefault(rule_id, 0)
        rule_stats[rule_id] += count
    return rule_stats


def save_mkeventd_rules(rule_packs: Iterable[ec.ECRulePack]) -> None:
    ec.save_rule_packs(rule_packs, active_config.mkeventd_pprint_rules)


def export_mkp_rule_pack(rule_pack: ec.ECRulePack) -> None:
    ec.export_rule_pack(rule_pack, active_config.mkeventd_pprint_rules)
