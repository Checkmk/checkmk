#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable

from cmk.ec.export import ECRulePack, MkpRulePackProxy

from cmk.gui.wato.mkeventd import MatchItemGeneratorECRulePacksAndRules
from cmk.gui.watolib.search import MatchItem


def test_match_item_generator_ec_rule_packs_and_rules() -> None:
    mkp_rule_pack = MkpRulePackProxy("mkp_rule_pack_id")
    mkp_rule_pack.rule_pack = {
        "title": "MKP Rule pack",
        "id": "mkp_rule_pack_id",
        "rules": [{"id": "mkp_rule_id", "description": "descr", "comment": "comment"}],
    }
    rule_packs: Iterable[ECRulePack] = [
        {
            "title": "Rule pack",
            "id": "rule_pack_id",
            "rules": [{"id": "rule_id", "description": "descr", "comment": ""}],
        },
        mkp_rule_pack,
    ]

    assert list(
        MatchItemGeneratorECRulePacksAndRules(
            "event_console",
            lambda: rule_packs,
        ).generate_match_items()
    ) == [
        MatchItem(
            title="rule_pack_id (Rule pack)",
            topic="Event Console rule packs",
            url="wato.py?mode=mkeventd_rules&rule_pack=rule_pack_id",
            match_texts=["rule pack", "rule_pack_id"],
        ),
        MatchItem(
            title="rule_id (descr)",
            topic="Event Console rules",
            url="wato.py?edit=0&mode=mkeventd_edit_rule&rule_pack=rule_pack_id",
            match_texts=["rule_id", "descr"],
        ),
        MatchItem(
            title="mkp_rule_pack_id (MKP Rule pack)",
            topic="Event Console rule packs",
            url="wato.py?mode=mkeventd_rules&rule_pack=mkp_rule_pack_id",
            match_texts=["mkp rule pack", "mkp_rule_pack_id"],
        ),
        MatchItem(
            title="mkp_rule_id (descr)",
            topic="Event Console rules",
            url="wato.py?edit=0&mode=mkeventd_edit_rule&rule_pack=mkp_rule_pack_id",
            match_texts=["mkp_rule_id", "descr", "comment"],
        ),
    ]
