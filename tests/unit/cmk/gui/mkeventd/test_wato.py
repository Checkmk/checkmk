#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from datetime import datetime, UTC
from typing import cast
from unittest.mock import Mock  # Import Mock

import pytest
import time_machine
from pytest import MonkeyPatch

import cmk.ec.export as ec
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.translations import TranslationOptions
from cmk.gui.config import Config
from cmk.gui.logged_in import user
from cmk.gui.mkeventd import wato as mkeventd_wato
from cmk.gui.search.matchers import MatchItem, MatchItemConfig
from cmk.gui.utils.roles import UserPermissions
from cmk.livestatus_client import SiteConfiguration, SiteConfigurations
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.fake_site import no_site_configuration


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
        ).generate_match_items(
            UserPermissions({}, {}, {}, []), MatchItemConfig.from_config(Config())
        )
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


@time_machine.travel(datetime.fromtimestamp(1622638021, tz=UTC))
def test_send_event(monkeypatch: MonkeyPatch) -> None:
    mock_sites = Mock()

    mock_sites.live.return_value = mock_sites

    monkeypatch.setattr(mkeventd_wato, "sites", mock_sites)
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


_RULE_PACK = ec.ECRulePackSpec(id="pack", title="Pack", disabled=False, rules=[])


def _simulator(
    *,
    simulated_site: SiteId,
    text: str = "Still nothing happened.",
    host: HostName = HostName("myhost089"),
    hostname_translation: TranslationOptions | None = None,
) -> mkeventd_wato.EventSimulator:
    return mkeventd_wato.EventSimulator(
        ec.Event(
            text=text,
            application="Foobar-Daemon",
            host=host,
            ipaddress="1.2.3.4",
            priority=5,
            facility=1,
            sl=0,
            site=simulated_site,
        ),
        SiteConfigurations({simulated_site: _site_configuration(simulated_site)}),
        hostname_translation or TranslationOptions(),
    )


def _simulate(rule: ec.Rule, *, simulated_site: SiteId) -> ec.MatchResult:
    return _simulator(simulated_site=simulated_site).match_rule(_RULE_PACK, rule)


def _site_configuration(site_id: SiteId) -> SiteConfiguration:
    site_config = no_site_configuration()
    site_config["id"] = site_id
    return site_config


def test_simulated_event_matches_rule_for_the_simulated_site() -> None:
    result = _simulate(
        ec.Rule(id="rule", match_site=[SiteId("remote")]), simulated_site=SiteId("remote")
    )

    assert isinstance(result, ec.MatchSuccess)


def test_simulated_event_does_not_match_rule_for_the_gui_site() -> None:
    result = _simulate(ec.Rule(id="rule", match_site=[omd_site()]), simulated_site=SiteId("remote"))

    assert result == ec.MatchFailure(reason="The site does not match.")


@pytest.mark.usefixtures("request_context")
def test_simulator_queries_time_periods_of_the_local_site_without_the_gui_connection(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    # The GUI has no connection to its own site if the user disabled it in the site status snap-in.
    mock_livestatus.add_table("timeperiods", [{"name": "workhours", "in": 0}], site=omd_site())
    mock_livestatus.expect_query("GET timeperiods\nColumns: name in", sites=[omd_site()])

    with mock_livestatus(expect_status_query=False):
        result = _simulate(
            ec.Rule(id="rule", match_timeperiod=ec.TimeperiodName("workhours")),
            simulated_site=omd_site(),
        )

    assert result == ec.MatchFailure(
        reason="The time period workhours is not is not known or is currently not active"
    )


@pytest.mark.usefixtures("request_context", "with_user_login")
def test_missing_connection_to_a_site_disabled_in_the_site_status_snapin_is_explained(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    user.disable_site(SiteId("disabled"))

    with (
        mock_livestatus(expect_status_query=True),
        pytest.raises(MKGeneralException, match='disabled in the "Site status" snap-in'),
    ):
        _simulate(
            ec.Rule(id="rule", match_timeperiod=ec.TimeperiodName("workhours")),
            simulated_site=SiteId("disabled"),
        )


@pytest.mark.usefixtures("request_context")
def test_simulated_event_uses_time_periods_of_the_simulated_site(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("timeperiods", [{"name": "workhours", "in": 1}], site=omd_site())
    mock_livestatus.add_table("timeperiods", [{"name": "workhours", "in": 0}], site="remote")
    mock_livestatus.expect_query("GET timeperiods\nColumns: name in", sites=["remote"])

    with mock_livestatus(expect_status_query=True):
        result = _simulate(
            ec.Rule(id="rule", match_timeperiod=ec.TimeperiodName("workhours")),
            simulated_site=SiteId("remote"),
        )

    assert isinstance(result, ec.MatchFailure)


@pytest.mark.usefixtures("request_context")
def test_simulator_fails_without_a_connection_to_the_simulated_site(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=True), pytest.raises(MKGeneralException):
        _simulate(
            ec.Rule(id="rule", match_timeperiod=ec.TimeperiodName("workhours")),
            simulated_site=SiteId("unconnected"),
        )


@pytest.mark.usefixtures("request_context")
def test_simulator_queries_time_periods_once_for_all_rules(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("timeperiods", [{"name": "workhours", "in": 1}], site="remote")
    mock_livestatus.expect_query("GET timeperiods\nColumns: name in", sites=["remote"])
    simulator = _simulator(simulated_site=SiteId("remote"))
    rules = [
        ec.Rule(id=f"rule{nr}", match_timeperiod=ec.TimeperiodName("workhours")) for nr in range(2)
    ]

    with mock_livestatus(expect_status_query=True):
        results = [simulator.match_rule(_RULE_PACK, rule) for rule in rules]

    assert all(isinstance(result, ec.MatchSuccess) for result in results)


def test_simulator_translates_the_host_name_once_for_all_rules() -> None:
    simulator = _simulator(
        simulated_site=SiteId("remote"),
        hostname_translation=TranslationOptions(regex=[("(.*)", "translated_\\1")]),
    )
    rules = [ec.Rule(id=f"rule{nr}", match_host="translated_myhost089") for nr in range(2)]

    results = [simulator.match_rule(_RULE_PACK, rule) for rule in rules]

    assert all(isinstance(result, ec.MatchSuccess) for result in results)


def test_simulator_matches_an_invalid_host_name_like_an_empty_one() -> None:
    # The simulator form accepts any host name without spaces, just like the Event Console.
    simulator = _simulator(simulated_site=SiteId("remote"), host=cast(HostName, "user@host"))

    result = simulator.match_rule(_RULE_PACK, ec.Rule(id="rule", match_host="^$"))

    assert isinstance(result, ec.MatchSuccess)


def test_simulator_matches_like_an_empty_host_name_if_the_translation_fails() -> None:
    # Nobody validates settings written by hand.
    simulator = _simulator(
        simulated_site=SiteId("remote"),
        hostname_translation=TranslationOptions(regex=[("((", "x")]),
    )

    result = simulator.match_rule(_RULE_PACK, ec.Rule(id="rule", match_host="^$"))

    assert isinstance(result, ec.MatchSuccess)


@pytest.mark.usefixtures("request_context")
def test_hostname_translation_of_a_site_is_its_site_specific_one() -> None:
    site_config = _site_configuration(SiteId("remote"))
    site_config["globals"] = {"hostname_translation": TranslationOptions(drop_domain=True)}

    translation = mkeventd_wato.hostname_translation_of_site(
        SiteId("remote"), SiteConfigurations({SiteId("remote"): site_config})
    )

    assert translation == TranslationOptions(drop_domain=True)


def test_match_groups_of_a_match_come_from_the_message_text() -> None:
    result = _simulator(simulated_site=SiteId("remote"), text="disk sda failed").match_rule(
        _RULE_PACK, ec.Rule(id="rule", match="disk (\\S+) failed")
    )

    assert isinstance(result, ec.MatchSuccess)
    assert mkeventd_wato.message_match_groups_text(result) == "sda"


def test_match_groups_of_a_cancelling_match_come_from_the_cancelling_text() -> None:
    result = _simulator(simulated_site=SiteId("remote"), text="disk sda ok").match_rule(
        _RULE_PACK, ec.Rule(id="rule", match="disk (\\S+) failed", match_ok="disk (\\S+) ok")
    )

    assert isinstance(result, ec.MatchSuccess)
    assert mkeventd_wato.message_match_groups_text(result) == "sda"


def test_match_groups_which_did_not_participate_in_a_match_show_up_as_none() -> None:
    result = _simulator(simulated_site=SiteId("remote"), text="disk sda").match_rule(
        _RULE_PACK, ec.Rule(id="rule", match="disk (\\S+)( failed)?")
    )

    assert isinstance(result, ec.MatchSuccess)
    assert mkeventd_wato.message_match_groups_text(result) == "sda,(none)"


_MATCHING_RULE = ec.Rule(id="matching", match="nothing")
_NON_MATCHING_RULE = ec.Rule(id="non_matching", match="no such text")
_CANCELLING_RULE = ec.Rule(id="cancelling", match="no such text", match_ok="nothing")
_SKIPPING_RULE = ec.Rule(id="skipping", match="nothing", drop="skip_pack")


def _rule_pack(*rules: ec.Rule) -> ec.ECRulePackSpec:
    return ec.ECRulePackSpec(id="pack", title="Pack", disabled=False, rules=list(rules))


def test_first_matching_rule_decides_the_match_of_a_rule_pack() -> None:
    simulator = _simulator(simulated_site=SiteId("remote"))
    rule_pack = _rule_pack(_NON_MATCHING_RULE, _MATCHING_RULE, _CANCELLING_RULE)

    pack_match = simulator.match_rule_pack(rule_pack)

    assert pack_match.first_match == simulator.match_rule(rule_pack, _MATCHING_RULE)


@pytest.mark.parametrize(
    "rules, skips_pack",
    [
        pytest.param([_SKIPPING_RULE, _MATCHING_RULE], True, id="first match skips"),
        pytest.param([_MATCHING_RULE, _SKIPPING_RULE], False, id="later match skips"),
    ],
)
def test_rule_pack_is_skipped_only_if_its_first_match_skips_it(
    rules: list[ec.Rule], skips_pack: bool
) -> None:
    pack_match = _simulator(simulated_site=SiteId("remote")).match_rule_pack(_rule_pack(*rules))

    assert pack_match.first_match_skips_pack is skips_pack


def test_rule_pack_match_counts_all_matching_rules() -> None:
    pack_match = _simulator(simulated_site=SiteId("remote")).match_rule_pack(
        _rule_pack(_SKIPPING_RULE, _NON_MATCHING_RULE, _MATCHING_RULE)
    )

    assert pack_match.matching_rules == 2
