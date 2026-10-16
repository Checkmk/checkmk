#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime, UTC
from types import FrameType
from typing import cast
from unittest.mock import Mock  # Import Mock

import pytest
import time_machine
from pytest import MonkeyPatch

import cmk.ec.export as ec
import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.translations import TranslationOptions
from cmk.gui.exceptions import RequestTimeout
from cmk.gui.logged_in import user
from cmk.gui.mkeventd import wato as mkeventd_wato
from cmk.gui.mkeventd.wato import MatchOutcome
from cmk.gui.search import MatchItem
from cmk.gui.utils.roles import UserPermissions
from cmk.livestatus_client import SingleSiteConnection, SiteConfiguration, SiteConfigurations
from cmk.livestatus_client.testing import MockLiveStatusConnection


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
        ).generate_match_items(UserPermissions({}, {}, {}, []))
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


def _rule_pack(*rules: ec.Rule, disabled: bool = False) -> ec.ECRulePackSpec:
    return ec.ECRulePackSpec(id="pack", title="Pack", disabled=disabled, rules=list(rules))


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
    return _simulator(simulated_site=simulated_site).match_rule(_rule_pack(), rule)


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

    assert result == ec.MatchFailure(reason="The time period workhours is currently not active")


@pytest.mark.usefixtures("request_context", "with_user_login")
def test_missing_connection_to_a_site_disabled_in_the_site_status_snapin_is_explained(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    user.disable_site(SiteId("disabled"))

    with mock_livestatus(expect_status_query=True):
        result = _simulate(
            ec.Rule(id="rule", match_timeperiod=ec.TimeperiodName("workhours")),
            simulated_site=SiteId("disabled"),
        )

    assert result == mkeventd_wato.UnknownMatch(
        reason="Cannot look up the time periods: The GUI has no Livestatus connection to site "
        'disabled, because the site is disabled in the "Site status" snap-in.'
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

    assert result == ec.MatchFailure(reason="The time period workhours is currently not active")


@pytest.mark.usefixtures("request_context")
def test_match_is_unknown_without_a_connection_to_the_simulated_site(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=True):
        result = _simulate(
            ec.Rule(id="rule", match_timeperiod=ec.TimeperiodName("workhours")),
            simulated_site=SiteId("unconnected"),
        )

    assert result == mkeventd_wato.UnknownMatch(
        reason="Cannot look up the time periods: The GUI has no Livestatus connection to site "
        "unconnected."
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
        results = [simulator.match_rule(_rule_pack(), rule) for rule in rules]

    assert all(isinstance(result, ec.MatchSuccess) for result in results)


@pytest.mark.usefixtures("request_context")
def test_simulator_gives_up_on_time_periods_after_the_first_failed_query(
    mock_livestatus: MockLiveStatusConnection, caplog: pytest.LogCaptureFixture
) -> None:
    simulator = _simulator(simulated_site=SiteId("unconnected"))
    rules = [
        ec.Rule(id=f"rule{nr}", match_timeperiod=ec.TimeperiodName("workhours")) for nr in range(2)
    ]

    with mock_livestatus(expect_status_query=True):
        results = [simulator.match_rule(_rule_pack(), rule) for rule in rules]

    assert caplog.messages.count("Cannot update time period information.") == 1
    assert results == 2 * [
        mkeventd_wato.UnknownMatch(
            reason="Cannot look up the time periods: The GUI has no Livestatus connection to site "
            "unconnected."
        )
    ]


def test_simulator_translates_the_host_name_once_for_all_rules() -> None:
    simulator = _simulator(
        simulated_site=SiteId("remote"),
        hostname_translation=TranslationOptions(regex=[("(.*)", "translated_\\1")]),
    )
    rules = [ec.Rule(id=f"rule{nr}", match_host="translated_myhost089") for nr in range(2)]

    results = [simulator.match_rule(_rule_pack(), rule) for rule in rules]

    assert all(isinstance(result, ec.MatchSuccess) for result in results)


def test_simulator_matches_an_invalid_host_name_like_an_empty_one() -> None:
    # The simulator form accepts any host name without spaces, just like the Event Console.
    simulator = _simulator(simulated_site=SiteId("remote"), host=cast(HostName, "user@host"))

    result = simulator.match_rule(_rule_pack(), ec.Rule(id="rule", match_host="^$"))

    assert isinstance(result, ec.MatchSuccess)


def test_simulator_matches_like_an_empty_host_name_if_the_translation_fails() -> None:
    # Nobody validates settings written by hand.
    simulator = _simulator(
        simulated_site=SiteId("remote"),
        hostname_translation=TranslationOptions(regex=[("((", "x")]),
    )

    result = simulator.match_rule(_rule_pack(), ec.Rule(id="rule", match_host="^$"))

    assert isinstance(result, ec.MatchSuccess)


def test_hand_written_hostname_translation_of_the_local_site_overrides_the_one_of_setup() -> None:
    paths = ec.create_paths(cmk.utils.paths.omd_root)
    (paths.config_dir.value / "wato").mkdir(parents=True, exist_ok=True)
    (paths.config_dir.value / "wato/global.mk").write_text(
        'hostname_translation = {"case": "lower"}\n'
    )
    paths.main_config_file.value.write_text('hostname_translation = {"case": "upper"}\n')

    translation = mkeventd_wato.hostname_translation_of_site(
        omd_site(), SiteConfigurations({omd_site(): _site_configuration(omd_site())})
    )

    assert translation == TranslationOptions(case="upper")


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
        _rule_pack(), ec.Rule(id="rule", match="disk (\\S+) failed")
    )

    assert isinstance(result, ec.MatchSuccess)
    assert mkeventd_wato.message_match_groups_text(result) == "sda"


def test_match_groups_of_a_cancelling_match_come_from_the_cancelling_text() -> None:
    result = _simulator(simulated_site=SiteId("remote"), text="disk sda ok").match_rule(
        _rule_pack(), ec.Rule(id="rule", match="disk (\\S+) failed", match_ok="disk (\\S+) ok")
    )

    assert isinstance(result, ec.MatchSuccess)
    assert mkeventd_wato.message_match_groups_text(result) == "sda"


def test_match_groups_which_did_not_participate_in_a_match_show_up_as_none() -> None:
    result = _simulator(simulated_site=SiteId("remote"), text="disk sda").match_rule(
        _rule_pack(), ec.Rule(id="rule", match="disk (\\S+)( failed)?")
    )

    assert isinstance(result, ec.MatchSuccess)
    assert mkeventd_wato.message_match_groups_text(result) == "sda,(none)"


def test_an_inverted_match_has_no_match_groups() -> None:
    result = _simulator(simulated_site=SiteId("remote"), text="disk sda").match_rule(
        _rule_pack(), ec.Rule(id="rule", match="disk (\\S+) failed", invert_matching=True)
    )

    assert isinstance(result, ec.MatchSuccess)
    assert mkeventd_wato.message_match_groups_text(result) == ""


_MATCHING_RULE = ec.Rule(id="matching", match="nothing")
_NON_MATCHING_RULE = ec.Rule(id="non_matching", match="no such text")
_CANCELLING_RULE = ec.Rule(id="cancelling", match="no such text", match_ok="nothing")
_DROPPING_RULE = ec.Rule(id="dropping", match="nothing", drop=True)
_CANCELLING_DROPPING_RULE = ec.Rule(
    id="cancelling_dropping", match="no such text", match_ok="nothing", drop=True
)
_SKIPPING_RULE = ec.Rule(id="skipping", match="nothing", drop="skip_pack")
_CANCELLING_SKIPPING_RULE = ec.Rule(
    id="cancelling_skipping", match="no such text", match_ok="nothing", drop="skip_pack"
)


@pytest.mark.parametrize(
    "rule, outcome",
    [
        pytest.param(_MATCHING_RULE, MatchOutcome.NEW_EVENT, id="match"),
        pytest.param(_CANCELLING_RULE, MatchOutcome.CANCEL_EVENTS, id="cancel"),
        pytest.param(_DROPPING_RULE, MatchOutcome.DROP_MESSAGE, id="drop"),
        pytest.param(_CANCELLING_DROPPING_RULE, MatchOutcome.DROP_MESSAGE, id="cancel, drop"),
        pytest.param(_SKIPPING_RULE, MatchOutcome.SKIP_PACK, id="skip"),
        pytest.param(_CANCELLING_SKIPPING_RULE, MatchOutcome.SKIP_PACK, id="cancel, skip"),
    ],
)
def test_match_outcome_is_the_one_of_the_event_console(
    rule: ec.Rule, outcome: MatchOutcome
) -> None:
    result = _simulate(rule, simulated_site=SiteId("remote"))

    assert isinstance(result, ec.MatchSuccess)
    assert mkeventd_wato.match_outcome(rule, result) is outcome


@pytest.mark.parametrize(
    "drop, outcome",
    [
        pytest.param(1, MatchOutcome.DROP_MESSAGE, id="true value"),
        pytest.param(0, MatchOutcome.NEW_EVENT, id="false value"),
    ],
)
def test_match_outcome_uses_the_truth_value_of_drop_like_the_event_console(
    drop: int, outcome: MatchOutcome
) -> None:
    # Nobody validates rule packs written by hand or shipped in an MKP.
    rule = ec.Rule(id="rule", match="nothing", drop=drop)  # type: ignore[typeddict-item]
    result = _simulate(rule, simulated_site=SiteId("remote"))

    assert isinstance(result, ec.MatchSuccess)
    assert mkeventd_wato.match_outcome(rule, result) is outcome


def _first_match_outcome(*rules: ec.Rule) -> MatchOutcome | None:
    pack_match = _simulator(simulated_site=SiteId("remote")).match_rule_pack(_rule_pack(*rules))
    return pack_match.first_match.outcome if pack_match.first_match else None


def test_first_matching_rule_decides_the_outcome_of_a_rule_pack() -> None:
    outcome = _first_match_outcome(_NON_MATCHING_RULE, _MATCHING_RULE, _CANCELLING_RULE)

    assert outcome is MatchOutcome.NEW_EVENT


@pytest.mark.parametrize(
    "rules, outcome",
    [
        pytest.param([_SKIPPING_RULE, _MATCHING_RULE], MatchOutcome.SKIP_PACK, id="first skips"),
        pytest.param([_MATCHING_RULE, _SKIPPING_RULE], MatchOutcome.NEW_EVENT, id="later skips"),
    ],
)
def test_rule_pack_is_skipped_only_if_its_first_match_skips_it(
    rules: list[ec.Rule], outcome: MatchOutcome
) -> None:
    assert _first_match_outcome(*rules) is outcome


def test_rule_pack_match_counts_all_matching_rules() -> None:
    pack_match = _simulator(simulated_site=SiteId("remote")).match_rule_pack(
        _rule_pack(_SKIPPING_RULE, _NON_MATCHING_RULE, _MATCHING_RULE)
    )

    assert pack_match.matching_rules == 2


def test_rule_with_an_invalid_regular_expression_does_not_match() -> None:
    result = _simulate(ec.Rule(id="rule", match="disk (("), simulated_site=SiteId("remote"))

    assert isinstance(result, ec.MatchFailure)
    assert result.reason.startswith("Cannot compile the rule: ")


def test_unexpected_errors_while_matching_a_rule_are_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Nobody validates rule packs written by hand or shipped in an MKP.
    rule = ec.Rule(id="rule", match_priority=5)  # type: ignore[typeddict-item]

    _simulate(rule, simulated_site=SiteId("remote"))

    assert "Cannot match rule pack/rule against the simulated event" in caplog.messages


@pytest.mark.usefixtures("request_context")
def test_rule_pack_match_has_the_unknown_matches_before_its_first_match(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    unknown_rule = ec.Rule(id="unknown", match_timeperiod=ec.TimeperiodName("workhours"))

    with mock_livestatus(expect_status_query=True):
        pack_match = _simulator(simulated_site=SiteId("unconnected")).match_rule_pack(
            _rule_pack(unknown_rule, _MATCHING_RULE, unknown_rule)
        )

    assert pack_match.unknown_matches == (
        mkeventd_wato.UnknownMatch(
            reason="Cannot look up the time periods: The GUI has no Livestatus connection to site "
            "unconnected."
        ),
    )


@contextmanager
def _request_timeout_after(seconds: float) -> Iterator[None]:
    """Times out the request like the GUI does, but after less than a second"""

    def raise_request_timeout(_signum: int, _frame: FrameType | None) -> None:
        raise RequestTimeout("Your request timed out.")

    previous_handler = signal.signal(signal.SIGALRM, raise_request_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


# Matching this pattern against this text takes seconds because of catastrophic backtracking, much
# longer than the request timeouts below, but a test still ends if its timeout doesn't work.
_SLOW_PATTERN = "(a+)+$"
_SLOW_TEXT = "a" * 26 + "b"


def test_request_timeout_while_matching_a_rule_aborts_the_request() -> None:
    simulator = _simulator(simulated_site=SiteId("remote"), text=_SLOW_TEXT)
    rule = ec.Rule(id="rule", match=_SLOW_PATTERN)

    with _request_timeout_after(0.01), pytest.raises(RequestTimeout):
        simulator.match_rule(_rule_pack(), rule)


def test_request_timeout_while_translating_the_host_name_aborts_the_request() -> None:
    hostname_translation = TranslationOptions(regex=[(_SLOW_PATTERN, "translated")])

    with _request_timeout_after(0.01), pytest.raises(RequestTimeout):
        _simulator(
            simulated_site=SiteId("remote"),
            host=HostName(_SLOW_TEXT),
            hostname_translation=hostname_translation,
        )


@pytest.mark.usefixtures("request_context")
def test_request_timeout_while_looking_up_time_periods_aborts_the_request(
    mock_livestatus: MockLiveStatusConnection, monkeypatch: MonkeyPatch
) -> None:
    def receive_data_timing_out(_self: object, _size: int, _timeout: float | None = None) -> bytes:
        raise RequestTimeout("Your request timed out.")

    # The Livestatus client turns this into an error of its own.
    monkeypatch.setattr(SingleSiteConnection, "receive_data", receive_data_timing_out)
    mock_livestatus.add_table("timeperiods", [{"name": "workhours", "in": 1}], site=omd_site())
    mock_livestatus.expect_query("GET timeperiods\nColumns: name in", sites=[omd_site()])

    with mock_livestatus(expect_status_query=False), pytest.raises(RequestTimeout):
        _simulate(
            ec.Rule(id="rule", match_timeperiod=ec.TimeperiodName("workhours")),
            simulated_site=omd_site(),
        )


def test_simulator_leaves_the_rule_unchanged() -> None:
    rule = ec.Rule(id="rule", state=("text_pattern", {"2": "ERROR"}))

    _simulate(rule, simulated_site=SiteId("remote"))

    assert rule == ec.Rule(id="rule", state=("text_pattern", {"2": "ERROR"}))


def test_disabled_rules_do_not_match_in_a_rule_pack() -> None:
    disabled_rule = ec.Rule(id="disabled", match="nothing", disabled=True)

    pack_match = _simulator(simulated_site=SiteId("remote")).match_rule_pack(
        _rule_pack(disabled_rule)
    )

    assert pack_match == mkeventd_wato.RulePackMatch(
        matching_rules=0, first_match=None, unknown_matches=()
    )


def test_rules_of_a_disabled_rule_pack_do_not_match() -> None:
    result = _simulator(simulated_site=SiteId("remote")).match_rule(
        _rule_pack(disabled=True), ec.Rule(id="rule", match="nothing")
    )

    assert result == ec.MatchFailure(reason="The rule pack is disabled.")
