#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from datetime import datetime

from freezegun import freeze_time
from pytest import MonkeyPatch

from livestatus import SiteId

from cmk.ec.export import ECRulePack, Event, MkpRulePackProxy

from cmk.gui.mkeventd import wato as mkeventd_wato
from cmk.gui.watolib.search import MatchItem


def test_match_item_generator_ec_rule_packs_and_rules() -> None:
    mkp_rule_pack = MkpRulePackProxy("mkp_rule_pack_id")
    mkp_rule_pack.rule_pack = {
        "title": "MKP Rule pack",
        "id": "mkp_rule_pack_id",
        "rules": [{"id": "mkp_rule_id", "description": "descr", "comment": "comment"}],
        "disabled": False,
    }
    rule_packs: Iterable[ECRulePack] = [
        {
            "title": "Rule pack",
            "id": "rule_pack_id",
            "rules": [{"id": "rule_id", "description": "descr", "comment": ""}],
            "disabled": False,
        },
        mkp_rule_pack,
    ]

    assert list(
        mkeventd_wato.MatchItemGeneratorECRulePacksAndRules(
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


@freeze_time(datetime.utcfromtimestamp(1622638021))
def test_send_event(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        mkeventd_wato,
        "execute_command",
        lambda *args, **kwargs: None,
    )
    assert (
        mkeventd_wato.send_event(
            Event(
                facility=17,
                priority=1,
                sl=20,
                host="horst",
                ipaddress="127.0.0.1",
                application="Barz App",
                text="I am a unit test",
                site=SiteId("heute"),
            )
        )
        == '<137>1 2021-06-02T12:47:01+00:00 horst - - - [Checkmk@18662 ipaddress="127.0.0.1" sl="20" application="Barz App"] I am a unit test'
    )
