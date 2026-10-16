#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from datetime import datetime, timezone

import pytest
import time_machine
from pytest import MonkeyPatch

from livestatus import SiteConfiguration, SiteConfigurations, SiteId

from cmk.ccc.site import omd_site

from cmk.utils.hostaddress import HostName

import cmk.ec.export as ec

from cmk.gui.mkeventd import wato as mkeventd_wato
from cmk.gui.watolib.search import MatchItem


def test_match_item_generator_ec_rule_packs_and_rules() -> None:
    mkp_rule_pack = ec.MkpRulePackProxy("mkp_rule_pack_id")
    mkp_rule_pack.rule_pack = {
        "title": "MKP Rule pack",
        "id": "mkp_rule_pack_id",
        "rules": [ec.Rule(id="mkp_rule_id", description="descr", comment="comment")],
        "disabled": False,
    }
    rule_packs: Iterable[ec.ECRulePack] = [
        {
            "title": "Rule pack",
            "id": "rule_pack_id",
            "rules": [ec.Rule(id="rule_id", description="descr", comment="")],
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


@time_machine.travel(datetime.fromtimestamp(1622638021, tz=timezone.utc))
def test_send_event(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        mkeventd_wato,
        "execute_command",
        lambda *args, **kwargs: None,
    )
    assert (
        mkeventd_wato.send_event(
            ec.Event(
                facility=17,
                priority=1,
                sl=20,
                host=HostName("horst"),
                ipaddress="127.0.0.1",
                application="Barz App",
                text="I am a unit test",
                site=SiteId("heute"),
            )
        )
        == '<137>1 2021-06-02T12:47:01+00:00 horst - - - [Checkmk@18662 ipaddress="127.0.0.1" sl="20" application="Barz App"] I am a unit test'
    )


def _simulate_event_for_site(*, match_site: SiteId, simulated_site: SiteId) -> ec.MatchResult:
    return mkeventd_wato.match_event_rule(
        ec.ECRulePackSpec(id="pack", title="Pack", disabled=False, rules=[]),
        ec.Rule(id="rule", match_site=[match_site]),
        ec.Event(
            text="Still nothing happened.",
            application="Foobar-Daemon",
            host=HostName("myhost089"),
            ipaddress="1.2.3.4",
            priority=5,
            facility=1,
            sl=0,
            site=simulated_site,
        ),
        SiteConfigurations({simulated_site: _site_configuration(simulated_site)}),
    )


def _site_configuration(site_id: SiteId) -> SiteConfiguration:
    return SiteConfiguration(
        {
            "id": site_id,
            "alias": f"Local site {site_id}",
            "socket": ("local", None),
            "disable_wato": True,
            "disabled": False,
            "insecure": False,
            "url_prefix": f"/{site_id}/",
            "multisiteurl": "",
            "persist": False,
            "replicate_ec": False,
            "replicate_mkps": False,
            "replication": None,
            "timeout": 5,
            "user_login": True,
            "proxy": None,
            "user_sync": "all",
            "status_host": None,
            "message_broker_port": 5672,
            "is_trusted": True,
        }
    )


@pytest.mark.usefixtures("patch_omd_site")
def test_simulated_event_matches_rule_for_the_simulated_site() -> None:
    result = _simulate_event_for_site(match_site=SiteId("remote"), simulated_site=SiteId("remote"))

    assert isinstance(result, ec.MatchSuccess)


@pytest.mark.usefixtures("patch_omd_site")
def test_simulated_event_does_not_match_rule_for_the_gui_site() -> None:
    result = _simulate_event_for_site(match_site=omd_site(), simulated_site=SiteId("remote"))

    assert result == ec.MatchFailure(reason="The site does not match.")
