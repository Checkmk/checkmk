#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import dataclasses
import io
import signal
import socket
import threading
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime, UTC
from pathlib import Path
from types import FrameType
from typing import cast
from unittest.mock import Mock  # Import Mock

import pytest
import time_machine
from pytest import MonkeyPatch

import cmk.ec.export as ec
import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.regex import RegexFutureWarning
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.translations import TranslationOptions
from cmk.ccc.version import Edition
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError, RequestTimeout
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.mkeventd import wato as mkeventd_wato
from cmk.gui.search.matchers import MatchItem, MatchItemConfig
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    ConfigVariable,
    EVENT_CONSOLE,
    GlobalSettingsContext,
)
from cmk.gui.watolib.site_changes import SiteChanges
from cmk.livestatus_client import SingleSiteConnection, SiteConfiguration, SiteConfigurations
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.web.utils.flashed_messages import get_flashed_messages
from tests.testlib.unit.fake_site import no_site_configuration
from tests.testlib.unit.gui.web_test_app import CmkTestResponse, SetConfig, WebTestAppForCMK
from tests.unit.cmk.gui.helpers.setup_mode_test_helper import (
    error_messages,
    form_values,
    icon_titles,
    link_vars,
    page_context,
    redirect_vars,
    render_page,
    set_request_vars,
    submit,
    table_rows,
    TableRow,
)


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


def _rule_pack(
    *rules: ec.Rule, disabled: bool = False, rule_pack_id: str = "pack"
) -> ec.ECRulePackSpec:
    return ec.ECRulePackSpec(
        id=rule_pack_id, title=rule_pack_id.title(), disabled=disabled, rules=list(rules)
    )


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
def test_rule_does_not_match_without_a_connection_if_its_time_period_does_not_decide(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=True):
        result = _simulate(
            ec.Rule(
                id="rule", match="no such text", match_timeperiod=ec.TimeperiodName("workhours")
            ),
            simulated_site=SiteId("unconnected"),
        )

    assert result == ec.MatchFailure(reason="did not match, message text does not match")


@pytest.mark.usefixtures("request_context")
def test_inverted_rule_matches_without_a_connection_if_its_time_period_does_not_decide(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=True):
        result = _simulate(
            ec.Rule(
                id="rule",
                match="no such text",
                match_timeperiod=ec.TimeperiodName("workhours"),
                invert_matching=True,
            ),
            simulated_site=SiteId("unconnected"),
        )

    assert isinstance(result, ec.MatchSuccess)


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


@pytest.mark.usefixtures("request_context")
def test_site_specific_hostname_translation_does_not_need_the_global_settings() -> None:
    global_settings_file = config_domain_registry[EVENT_CONSOLE].config_file(site_specific=False)
    global_settings_file.parent.mkdir(parents=True, exist_ok=True)
    global_settings_file.write_text("this is no valid Python (\n")
    site_config = _site_configuration(SiteId("remote"))
    site_config["globals"] = {"hostname_translation": TranslationOptions(drop_domain=True)}

    translation = mkeventd_wato.hostname_translation_of_site(
        SiteId("remote"), SiteConfigurations({SiteId("remote"): site_config})
    )

    assert translation == TranslationOptions(drop_domain=True)


@pytest.mark.usefixtures("request_context")
def test_hostname_translation_of_a_site_without_a_site_specific_one_is_the_global_one() -> None:
    config_domain_registry[EVENT_CONSOLE].save(
        {"hostname_translation": TranslationOptions(drop_domain=True)}
    )

    translation = mkeventd_wato.hostname_translation_of_site(
        SiteId("remote"),
        SiteConfigurations({SiteId("remote"): _site_configuration(SiteId("remote"))}),
    )

    assert translation == TranslationOptions(drop_domain=True)


@pytest.mark.usefixtures("request_context")
def test_hostname_translation_of_a_site_without_any_is_the_default_of_the_event_console() -> None:
    translation = mkeventd_wato.hostname_translation_of_site(
        SiteId("remote"),
        SiteConfigurations({SiteId("remote"): _site_configuration(SiteId("remote"))}),
    )

    assert translation == ec.default_config()["hostname_translation"]


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


def test_match_groups_which_did_not_participate_in_a_match_show_up_as_empty() -> None:
    result = _simulator(simulated_site=SiteId("remote"), text="disk sda").match_rule(
        _rule_pack(), ec.Rule(id="rule", match="disk (\\S+)( failed)?")
    )

    assert isinstance(result, ec.MatchSuccess)
    assert mkeventd_wato.message_match_groups_text(result) == "sda,(empty)"


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
        pytest.param(_MATCHING_RULE, ec.MatchOutcome.NEW_EVENT, id="match"),
        pytest.param(_CANCELLING_RULE, ec.MatchOutcome.CANCEL_EVENTS, id="cancel"),
        pytest.param(_DROPPING_RULE, ec.MatchOutcome.DROP_MESSAGE, id="drop"),
        pytest.param(_CANCELLING_DROPPING_RULE, ec.MatchOutcome.DROP_MESSAGE, id="cancel, drop"),
        pytest.param(_SKIPPING_RULE, ec.MatchOutcome.SKIP_PACK, id="skip"),
        pytest.param(_CANCELLING_SKIPPING_RULE, ec.MatchOutcome.SKIP_PACK, id="cancel, skip"),
    ],
)
def test_match_outcome_is_the_one_of_the_event_console(
    rule: ec.Rule, outcome: ec.MatchOutcome
) -> None:
    result = _simulate(rule, simulated_site=SiteId("remote"))

    assert isinstance(result, ec.MatchSuccess)
    assert ec.match_outcome(rule, result) is outcome


@pytest.mark.parametrize(
    "drop, outcome",
    [
        pytest.param(1, ec.MatchOutcome.DROP_MESSAGE, id="true value"),
        pytest.param(0, ec.MatchOutcome.NEW_EVENT, id="false value"),
    ],
)
def test_match_outcome_uses_the_truth_value_of_drop_like_the_event_console(
    drop: int, outcome: ec.MatchOutcome
) -> None:
    # Nobody validates rule packs written by hand or shipped in an MKP.
    rule = ec.Rule(id="rule", match="nothing", drop=drop)  # type: ignore[typeddict-item]
    result = _simulate(rule, simulated_site=SiteId("remote"))

    assert isinstance(result, ec.MatchSuccess)
    assert ec.match_outcome(rule, result) is outcome


def _first_match_outcome(*rules: ec.Rule) -> ec.MatchOutcome | None:
    pack_match = _simulator(simulated_site=SiteId("remote")).match_rule_pack(_rule_pack(*rules))
    return pack_match.first_match.outcome if pack_match.first_match else None


def test_first_matching_rule_decides_the_outcome_of_a_rule_pack() -> None:
    outcome = _first_match_outcome(_NON_MATCHING_RULE, _MATCHING_RULE, _CANCELLING_RULE)

    assert outcome is ec.MatchOutcome.NEW_EVENT


@pytest.mark.parametrize(
    "rules, outcome",
    [
        pytest.param([_SKIPPING_RULE, _MATCHING_RULE], ec.MatchOutcome.SKIP_PACK, id="first skips"),
        pytest.param([_MATCHING_RULE, _SKIPPING_RULE], ec.MatchOutcome.NEW_EVENT, id="later skips"),
    ],
)
def test_rule_pack_is_skipped_only_if_its_first_match_skips_it(
    rules: list[ec.Rule], outcome: ec.MatchOutcome
) -> None:
    assert _first_match_outcome(*rules) is outcome


def test_rule_pack_match_counts_all_matching_rules() -> None:
    pack_match = _simulator(simulated_site=SiteId("remote")).match_rule_pack(
        _rule_pack(_SKIPPING_RULE, _NON_MATCHING_RULE, _MATCHING_RULE)
    )

    assert pack_match.matching_rules == 2


@pytest.mark.parametrize(
    "rule_packs, decides",
    [
        pytest.param([], False, id="no rule packs"),
        pytest.param([_rule_pack(_NON_MATCHING_RULE)], False, id="no match"),
        pytest.param(
            [_rule_pack(_NON_MATCHING_RULE), _rule_pack(_MATCHING_RULE)], True, id="match"
        ),
        pytest.param([_rule_pack(_SKIPPING_RULE, _MATCHING_RULE)], False, id="skipped match"),
        pytest.param([_rule_pack(_MATCHING_RULE, disabled=True)], False, id="disabled rule pack"),
    ],
)
def test_a_rule_of_the_rule_packs_decides_unless_its_rule_pack_is_skipped(
    rule_packs: list[ec.ECRulePackSpec], decides: bool
) -> None:
    simulator = _simulator(simulated_site=SiteId("remote"))

    assert simulator.has_decisive_match(rule_packs) is decides


def test_rule_with_an_invalid_regular_expression_does_not_match() -> None:
    result = _simulate(ec.Rule(id="rule", match="disk (("), simulated_site=SiteId("remote"))

    assert isinstance(result, ec.MatchFailure)
    assert result.reason.startswith("Cannot compile the rule: ")


def test_unexpected_errors_while_matching_a_rule_are_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Nobody validates rule packs written by hand or shipped in an MKP.
    rule = ec.Rule(id="rule", match_sl=5)  # type: ignore[typeddict-item]

    _simulate(rule, simulated_site=SiteId("remote"))

    assert "Cannot match rule pack/rule against the simulated event" in caplog.messages


@pytest.mark.usefixtures("request_context")
def test_unexpected_errors_while_matching_a_rule_without_time_periods_are_logged(
    mock_livestatus: MockLiveStatusConnection, caplog: pytest.LogCaptureFixture
) -> None:
    # Compiling a rule checks its priority ranges, so only a broken event can still make matching
    # fail after looking up the time periods.
    simulator = _simulator(simulated_site=SiteId("unconnected"), text=None)  # type: ignore[arg-type]
    rule = ec.Rule(id="rule", match="disk", match_timeperiod=ec.TimeperiodName("workhours"))

    with mock_livestatus(expect_status_query=True):
        simulator.match_rule(_rule_pack(), rule)

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


# The Setup pages of the Event Console need a request of a logged-in user.
_setup_page = pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")


def _paths() -> ec.Paths:
    return ec.create_paths(cmk.utils.paths.omd_root)


def _mode[M: mkeventd_wato.ABCEventConsoleMode](
    mode_class: type[M], config: Config, edition: Edition
) -> M:
    return mode_class(edition, page_context(config))


def _stored(rule: ec.Rule) -> ec.Rule:
    """The rule with the attributes the rule editor always saves"""
    return ec.Rule(state=-1, sl=ec.ServiceLevel(value=0, precedence="message")) | rule


def _save_rule_packs(*rule_packs: ec.ECRulePack) -> None:
    ec.save_rule_packs(rule_packs, pretty_print=False, path=_paths().rule_pack_dir.value)


def _exported(rule_pack: ec.ECRulePackSpec) -> ec.MkpRulePackProxy:
    """Makes the rule pack available for packaging, like the rule pack list does"""
    ec.export_rule_pack(rule_pack, pretty_print=False, path=_paths().mkp_rule_pack_dir.value)
    return ec.MkpRulePackProxy(rule_pack["id"])


def _export_file(rule_pack_id: str = "pack") -> Path:
    return _paths().mkp_rule_pack_dir.value / f"{rule_pack_id}.mk"


def _stored_rule_pack(rule_pack_id: str = "pack") -> ec.ECRulePack:
    [rule_pack] = [rp for rp in ec.load_rule_packs(_paths()) if rp["id"] == rule_pack_id]
    return rule_pack


def _rule_pack_ids() -> list[str]:
    return [rule_pack["id"] for rule_pack in ec.load_rule_packs(_paths())]


def _rule_ids(rule_pack_id: str = "pack") -> list[str]:
    return [rule["id"] for rule in _stored_rule_pack(rule_pack_id)["rules"]]


def _pending_changes() -> list[tuple[str, Sequence[str]]]:
    return [(change["action_name"], change["domains"]) for change in SiteChanges(omd_site()).read()]


def _flashed_messages() -> list[str]:
    return [str(message.msg) for message in get_flashed_messages()]


def _status_icon_titles(row: TableRow) -> list[str]:
    """The tooltips of the icons in the table row, leaving out the ones of links and buttons"""
    titles = []
    for cell in row.values():
        without_links = copy.copy(cell)
        for link in without_links.select("a"):
            link.decompose()
        titles += icon_titles(without_links)
    return titles


def _event_console_status(
    replication_mode: str = "", *, success: int = 1, last_sync: float = 0
) -> dict[str, object]:
    return {
        "status_replication_slavemode": replication_mode,
        "status_replication_success": success,
        "status_replication_last_sync": last_sync,
    }


def _add_event_console_status(
    live: MockLiveStatusConnection, status: Mapping[str, object] | None
) -> None:
    """Lets the local Event Console report its status, or no status if it is not running"""
    # Unlike its mock, Livestatus answers a query without columns with their names first.
    columns = _event_console_status().keys() if status is None else status.keys()
    header = {column: column for column in columns}
    live.add_table(
        "eventconsolestatus",
        [header] if status is None else [header, dict(status)],
        site=omd_site(),
    )


_CENTRAL_STATUS = _event_console_status()


@contextmanager
def _local_event_console(
    live: MockLiveStatusConnection, status: Mapping[str, object] | None
) -> Iterator[None]:
    """Expects a page to ask the local Event Console for its status"""
    _add_event_console_status(live, status)
    live.expect_query("GET eventconsolestatus", sites=[omd_site()])
    with live(expect_status_query=False):
        yield


@contextmanager
def _rule_hit_queries(
    live: MockLiveStatusConnection, rule_hits: Iterable[tuple[str, str, int]] = ()
) -> Iterator[None]:
    """Expects a page to ask the Event Consoles of all sites for the (site, rule ID, hits)"""
    for site in live.sites:
        live.add_table(
            "eventconsolerules",
            [
                {"rule_id": rule_id, "rule_hits": hits}
                for hit_site, rule_id, hits in rule_hits
                if hit_site == site
            ],
            site=site,
        )
    live.expect_query("GET eventconsolerules\nColumns: rule_id rule_hits")
    with live(expect_status_query=True):
        yield


@contextmanager
def _rule_pack_list_queries(
    live: MockLiveStatusConnection,
    *,
    status: Mapping[str, object] | None = _CENTRAL_STATUS,
    rule_hits: Iterable[tuple[str, str, int]] = (),
) -> Iterator[None]:
    """Expects the rule pack list to ask the Event Consoles for their status and rule hits"""
    _add_event_console_status(live, status)
    with _rule_hit_queries(live, rule_hits):
        # The page asks the local Event Console for its replication mode before connecting to the
        # sites, i.e. before the status query of the connection, which the mock expects first.
        live.expect_query("GET eventconsolestatus", sites=[omd_site()], force_pos=0)
        yield


def _fill_in_the_simulator(text: str = "Still nothing happened.") -> None:
    """Fills in the event simulator like the user, changing only the text of the defaults"""
    set_request_vars(
        event_p_text=text,
        event_p_application="Foobar-Daemon",
        event_p_host="myhost089",
        event_p_ipaddress="1.2.3.4",
        event_p_priority=DropdownChoice.option_id(5),
        event_p_facility=DropdownChoice.option_id(1),
        event_p_sl=DropdownChoice.option_id(0),
        event_p_site=DropdownChoice.option_id(omd_site()),
    )


def _rule_pack_list(config: Config, edition: Edition) -> str:
    return render_page(_mode(mkeventd_wato.ModeEventConsoleRulePacks, config, edition), config)


def _rule_pack_list_action(config: Config, edition: Edition) -> ActionResult:
    return _mode(mkeventd_wato.ModeEventConsoleRulePacks, config, edition).action(config)


@_setup_page
def test_deleting_a_rule_pack_removes_it(load_config: Config, test_edition: Edition) -> None:
    _save_rule_packs(_rule_pack(rule_pack_id="first"), _rule_pack(rule_pack_id="second"))
    submit(_delete="0")

    result = _rule_pack_list_action(load_config, test_edition)

    assert _rule_pack_ids() == ["second"]
    assert redirect_vars(result) == {"mode": "mkeventd_rule_packs"}


@_setup_page
def test_deleting_a_rule_pack_is_a_pending_change_of_the_event_console(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack())
    submit(_delete="0")

    _rule_pack_list_action(load_config, test_edition)

    assert _pending_changes() == [("delete-rule-pack", [EVENT_CONSOLE])]


@_setup_page
def test_moving_a_rule_pack_reorders_the_rule_packs(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(rule_pack_id="first"), _rule_pack(rule_pack_id="second"))
    submit(_move="0", _index="1")

    _rule_pack_list_action(load_config, test_edition)

    assert _rule_pack_ids() == ["second", "first"]


@_setup_page
def test_exporting_a_rule_pack_offers_it_with_its_rules_for_packaging(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="rule"))))
    submit(_export="0")

    _rule_pack_list_action(load_config, test_edition)

    assert ec.RulePackType.type_of(_stored_rule_pack(), {}) is ec.RulePackType.exported
    assert _rule_ids() == ["rule"]


@_setup_page
def test_dissolving_an_exported_rule_pack_withdraws_it_from_packaging(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_exported(_rule_pack(_stored(ec.Rule(id="rule")))))
    submit(_dissolve="0")

    _rule_pack_list_action(load_config, test_edition)

    assert ec.RulePackType.type_of(_stored_rule_pack(), {}) is ec.RulePackType.internal
    assert _rule_ids() == ["rule"]
    assert not _export_file().exists()


def _rule_pack_modified_after_packaging() -> None:
    """Saves a rule pack, modified by adding a rule, and its version without it for packaging"""
    _exported(_rule_pack(_stored(ec.Rule(id="packaged"))))
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="packaged")), _stored(ec.Rule(id="added"))))


@_setup_page
def test_resetting_a_modified_rule_pack_restores_its_version_for_packaging(
    load_config: Config, test_edition: Edition
) -> None:
    _rule_pack_modified_after_packaging()
    submit(_reset="0")

    _rule_pack_list_action(load_config, test_edition)

    assert _rule_ids() == ["packaged"]


@_setup_page
def test_synchronizing_a_modified_rule_pack_puts_the_modification_into_its_packaging(
    load_config: Config, test_edition: Edition
) -> None:
    _rule_pack_modified_after_packaging()
    submit(_synchronize="0")

    _rule_pack_list_action(load_config, test_edition)

    assert ec.RulePackType.type_of(_stored_rule_pack(), {}) is ec.RulePackType.exported
    assert _rule_ids() == ["packaged", "added"]


@_setup_page
def test_dissolving_a_rule_pack_which_is_not_exported_is_refused(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack())
    submit(_dissolve="0")

    with pytest.raises(MKUserError, match="rule pack was not exported"):
        _rule_pack_list_action(load_config, test_edition)


@_setup_page
def test_resetting_the_counters_resets_them_in_the_event_console_of_the_site(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    submit(_reset_counters="1")
    mock_livestatus.expect_query(
        "COMMAND [...] EC_RESETCOUNTERS;", match_type="ellipsis", sites=[omd_site()]
    )

    with mock_livestatus(expect_status_query=True):
        _rule_pack_list_action(load_config, test_edition)


@contextmanager
def _event_daemon(answers: Mapping[bytes, bytes]) -> Iterator[None]:
    """Answers the queries on the status socket of the local event daemon"""
    socket_path = cmk.utils.paths.omd_root / "tmp/run/mkeventd/status"
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    stopped = threading.Event()

    def answer(server: socket.socket) -> None:
        while not stopped.is_set():
            try:
                connection, _address = server.accept()
            except TimeoutError:
                continue
            with connection, connection.makefile("rb") as query:
                connection.sendall(answers.get(query.read(), b""))

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(socket_path))
        server.listen()
        # Check now and then whether to stop, also when nobody connects.
        server.settimeout(0.01)
        thread = threading.Thread(target=answer, args=(server,), daemon=True)
        thread.start()
        try:
            yield
        finally:
            stopped.set()
            thread.join()
            socket_path.unlink()


@_setup_page
def test_copying_the_rules_of_the_central_site_replaces_the_local_ones(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(rule_pack_id="local"))
    submit(_copy_rules="1")

    with _event_daemon(
        {b"REPLICATE 0": repr({"rules": [_rule_pack(rule_pack_id="central")]}).encode()}
    ):
        _rule_pack_list_action(load_config, test_edition)

    assert _rule_pack_ids() == ["central"]


@pytest.mark.parametrize(
    "answer, error",
    [
        pytest.param(b"{}", "Cannot get rules from local event daemon", id="no rules"),
        pytest.param(b"{", "Invalid response from event daemon", id="invalid"),
    ],
)
@_setup_page
def test_copying_the_rules_of_the_central_site_fails_without_rules_from_the_event_daemon(
    answer: bytes, error: str, load_config: Config, test_edition: Edition
) -> None:
    submit(_copy_rules="1")

    with _event_daemon({b"REPLICATE 0": answer}), pytest.raises(MKGeneralException, match=error):
        _rule_pack_list_action(load_config, test_edition)


@_setup_page
def test_copying_the_rules_of_the_central_site_fails_without_a_running_event_daemon(
    load_config: Config, test_edition: Edition
) -> None:
    submit(_copy_rules="1")

    with pytest.raises(MKGeneralException, match="Cannot connect to event daemon"):
        _rule_pack_list_action(load_config, test_edition)


@_setup_page
def test_trying_out_an_event_keeps_it_for_the_simulator(
    load_config: Config, test_edition: Edition
) -> None:
    _fill_in_the_simulator("disk sda failed")
    submit(_simulate="1")

    _rule_pack_list_action(load_config, test_edition)

    assert user.load_file("simulated_event", {})["text"] == "disk sda failed"


@_setup_page
def test_generating_an_event_sends_it_to_the_event_console_of_its_site(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    _fill_in_the_simulator("disk sda failed")
    submit(_generate="1")
    mock_livestatus.expect_query(
        "COMMAND [...] EC_CREATE;<13>1 ... myhost089 ... disk sda failed",
        match_type="ellipsis",
        sites=[omd_site()],
    )

    with mock_livestatus(expect_status_query=True):
        _rule_pack_list_action(load_config, test_edition)

    assert "Test event generated and sent to Event Console." in _flashed_messages()[0]


@pytest.mark.parametrize(
    "field, error",
    [
        pytest.param("application", "Please specify an application name", id="application"),
        pytest.param("host", "Please specify a host name", id="host"),
    ],
)
@_setup_page
def test_generating_an_event_needs_its_origin(
    field: str, error: str, load_config: Config, test_edition: Edition
) -> None:
    _fill_in_the_simulator()
    submit(**{f"event_p_{field}": "", "_generate": "1"})

    with pytest.raises(MKUserError, match=error):
        _rule_pack_list_action(load_config, test_edition)


@_setup_page
def test_rule_pack_list_without_rule_packs_says_so(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    _save_rule_packs()

    with _rule_pack_list_queries(mock_livestatus):
        page = _rule_pack_list(load_config, test_edition)

    assert "You have not created any rule packs yet." in page


@_setup_page
def test_rule_pack_list_counts_the_rules_and_their_hits_on_all_sites(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="a")), _stored(ec.Rule(id="b"))))

    with _rule_pack_list_queries(
        mock_livestatus,
        rule_hits=[(omd_site(), "a", 2), ("remote", "a", 3), (omd_site(), "b", 1)],
    ):
        [row] = table_rows(_rule_pack_list(load_config, test_edition), "Rule packs")

    assert (row["Rules"].get_text(strip=True), row["Hits"].get_text(strip=True)) == ("2", "6")


@_setup_page
def test_rule_pack_search_without_a_match_says_so(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    _save_rule_packs(_rule_pack())
    set_request_vars(search="no such thing")

    with _local_event_console(mock_livestatus, _CENTRAL_STATUS):
        page = _rule_pack_list(load_config, test_edition)

    assert "Found no rule packs." in page


def _found_rule_packs(
    config: Config, edition: Edition, live: MockLiveStatusConnection
) -> list[TableRow]:
    _save_rule_packs(
        _rule_pack(_stored(ec.Rule(id="load", description="CPU load")), rule_pack_id="cpu"),
        _rule_pack(
            _stored(ec.Rule(id="failed", description="disk failed")), rule_pack_id="storage"
        ),
        _rule_pack(rule_pack_id="disks"),
    )
    set_request_vars(search="disk")
    with _rule_pack_list_queries(live):
        return table_rows(_rule_pack_list(config, edition), "Found rule packs")


@_setup_page
def test_rule_pack_search_finds_the_rule_packs_matching_by_title_or_by_a_rule(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    rows = _found_rule_packs(load_config, test_edition, mock_livestatus)

    assert [row["ID"].get_text() for row in rows] == ["storage", "disks"]


@_setup_page
def test_rule_pack_search_is_kept_when_looking_at_the_matching_rules(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    rows = _found_rule_packs(load_config, test_edition, mock_livestatus)

    assert [link_vars(row["Rules"]).get("search") for row in rows] == ["disk", None]


@_setup_page
def test_rule_pack_list_of_a_remote_replication_warns_that_its_rules_are_unused(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    with _rule_pack_list_queries(mock_livestatus, status=_event_console_status("sync")):
        page = _rule_pack_list(load_config, test_edition)

    assert "The rules edited here will not be used." in page


@_setup_page
def test_rule_pack_list_reports_a_stopped_event_console(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    with _rule_pack_list_queries(mock_livestatus, status=None):
        page = _rule_pack_list(load_config, test_edition)

    assert "The Event Console is currently not running." in page


@_setup_page
def test_rule_pack_list_marks_disabled_rule_packs(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    _save_rule_packs(_rule_pack(disabled=True))

    with _rule_pack_list_queries(mock_livestatus):
        [row] = table_rows(_rule_pack_list(load_config, test_edition), "Rule packs")

    assert _status_icon_titles(row) == [
        "This rule pack is currently disabled. None of its rules will be applied."
    ]


_MATCHES = "Number of matching rules in this pack: %d"


@pytest.mark.parametrize(
    "rules_of_rule_packs, titles",
    [
        pytest.param([[_NON_MATCHING_RULE]], [["None of the rules in this pack matches"]], id="no match"),
        pytest.param([[_NON_MATCHING_RULE, _MATCHING_RULE]], [[_MATCHES % 1]], id="match"),
        pytest.param([[_CANCELLING_RULE]], [[_MATCHES % 1 + ", first match is a cancelling match"]], id="cancel"),
        pytest.param([[_DROPPING_RULE]], [[_MATCHES % 1 + ", first match drops the message"]], id="drop"),
        pytest.param([[_SKIPPING_RULE, _MATCHING_RULE]], [[_MATCHES % 2 + ", the first match skips this rule pack"]], id="skip"),
        pytest.param([[ec.Rule(id="groups", match="(nothing)")]], [[_MATCHES % 1 + ", match groups of decisive match: nothing"]], id="match groups"),
        pytest.param([[_MATCHING_RULE], [_MATCHING_RULE]], [[_MATCHES % 1], [_MATCHES % 1 + ", but it is overruled by a match in a previous rule pack."]], id="overruled"),
        pytest.param([[_SKIPPING_RULE], [_MATCHING_RULE]], [[_MATCHES % 1 + ", the first match skips this rule pack"], [_MATCHES % 1]], id="skipped"),
    ],
)  # fmt: skip
@_setup_page
def test_rule_pack_list_shows_how_the_simulated_event_matches_each_rule_pack(
    rules_of_rule_packs: Sequence[Sequence[ec.Rule]],
    titles: Sequence[Sequence[str]],
    load_config: Config,
    test_edition: Edition,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _save_rule_packs(
        *(
            _rule_pack(*map(_stored, rules), rule_pack_id=f"pack{nr}")
            for nr, rules in enumerate(rules_of_rule_packs)
        )
    )
    _fill_in_the_simulator()
    set_request_vars(_simulate="1")

    with _rule_pack_list_queries(mock_livestatus):
        rows = table_rows(_rule_pack_list(load_config, test_edition), "Rule packs")

    assert [_status_icon_titles(row) for row in rows] == titles


def _rule_list_action(config: Config, edition: Edition) -> ActionResult:
    return _mode(mkeventd_wato.ModeEventConsoleRules, config, edition).action(config)


def _rule_list(config: Config, edition: Edition) -> str:
    set_request_vars(rule_pack="pack")
    return render_page(_mode(mkeventd_wato.ModeEventConsoleRules, config, edition), config)


def _listed_rule(
    rule: ec.Rule, config: Config, edition: Edition, live: MockLiveStatusConnection
) -> TableRow:
    _save_rule_packs(_rule_pack(_stored(rule)))
    with _rule_hit_queries(live):
        [row] = table_rows(_rule_list(config, edition), "Rules")
    return row


@_setup_page
def test_deleting_a_rule_removes_it_from_its_rule_pack(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="first")), _stored(ec.Rule(id="second"))))
    submit(rule_pack="pack", _delete="0")

    result = _rule_list_action(load_config, test_edition)

    assert _rule_ids() == ["second"]
    assert redirect_vars(result) == {"mode": "mkeventd_rules", "rule_pack": "pack"}


@_setup_page
def test_deleting_a_rule_of_an_exported_rule_pack_updates_the_export(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(
        _exported(_rule_pack(_stored(ec.Rule(id="first")), _stored(ec.Rule(id="second"))))
    )
    submit(rule_pack="pack", _delete="0")

    _rule_list_action(load_config, test_edition)

    assert _rule_ids() == ["second"]


@_setup_page
def test_moving_a_rule_reorders_the_rules_of_its_rule_pack(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="first")), _stored(ec.Rule(id="second"))))
    submit(rule_pack="pack", _move="0", _index="1")

    _rule_list_action(load_config, test_edition)

    assert _rule_ids() == ["second", "first"]


@_setup_page
def test_moving_a_rule_to_another_rule_pack_puts_it_first_there(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(
        _rule_pack(_stored(ec.Rule(id="a")), _stored(ec.Rule(id="b")), rule_pack_id="source"),
        _rule_pack(_stored(ec.Rule(id="c")), rule_pack_id="target"),
    )
    submit(rule_pack="source", _move_to="yes", _move_to_b="target")

    _rule_list_action(load_config, test_edition)

    assert (_rule_ids("source"), _rule_ids("target")) == (["a"], ["b", "c"])


@_setup_page
def test_moving_a_rule_to_an_exported_rule_pack_updates_the_export(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(
        _rule_pack(_stored(ec.Rule(id="a")), rule_pack_id="source"),
        _exported(_rule_pack(_stored(ec.Rule(id="b")), rule_pack_id="target")),
    )
    submit(rule_pack="source", _move_to="yes", _move_to_a="target")

    _rule_list_action(load_config, test_edition)

    assert _rule_ids("target") == ["a", "b"]


@_setup_page
def test_rules_of_an_unknown_rule_pack_are_refused(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack())
    set_request_vars(rule_pack="unknown")

    with pytest.raises(MKUserError, match="The requested rule pack does not exist."):
        _mode(mkeventd_wato.ModeEventConsoleRules, load_config, test_edition)


@_setup_page
def test_rule_list_of_an_empty_rule_pack_says_so(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack())

    assert "This package does not yet contain any rules." in _rule_list(load_config, test_edition)


@_setup_page
def test_rule_search_without_a_match_says_so(load_config: Config, test_edition: Edition) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="rule", description="disk failed"))))
    set_request_vars(search="cpu")

    assert "No rules found." in _rule_list(load_config, test_edition)


@pytest.mark.parametrize(
    "rule, state",
    [
        pytest.param(ec.Rule(id="rule", state=2), "CRIT", id="fixed"),
        pytest.param(ec.Rule(id="rule", state=-1), "(syslog)", id="syslog"),
        pytest.param(ec.Rule(id="rule", state=("text_pattern", {"2": "ERROR"})), "(set by message text)", id="text pattern"),
        pytest.param(ec.Rule(id="rule", drop=True), "DROP", id="drop"),
        pytest.param(ec.Rule(id="rule", drop="skip_pack"), "Skip pack", id="skip"),
    ],
)  # fmt: skip
@_setup_page
def test_rule_list_shows_the_outcome_of_each_rule(
    rule: ec.Rule,
    state: str,
    load_config: Config,
    test_edition: Edition,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    row = _listed_rule(rule, load_config, test_edition, mock_livestatus)

    assert row["State"].get_text(strip=True) == state


@pytest.mark.parametrize(
    "priorities, text",
    [
        pytest.param((2, 2), "crit", id="single"),
        pytest.param((4, 0), "wa..em", id="range"),
    ],
)
@_setup_page
def test_rule_list_shows_the_matched_syslog_priorities(
    priorities: tuple[int, int],
    text: str,
    load_config: Config,
    test_edition: Edition,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    row = _listed_rule(
        ec.Rule(id="rule", match_priority=priorities), load_config, test_edition, mock_livestatus
    )

    assert row["Priority"].get_text(strip=True) == text


@_setup_page
def test_rule_list_shows_the_matched_syslog_facility(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    row = _listed_rule(
        ec.Rule(id="rule", match_facility=4), load_config, test_edition, mock_livestatus
    )

    assert row["Facility"].get_text(strip=True) == "auth"


_CONTACT_GROUPS = "This rule attaches contact group(s) to the events: %s"
_ADMINS = ec.ContactGroups(groups=["admins"], notify=True, precedence="host")
_NOBODY = ec.ContactGroups(groups=[], notify=True, precedence="host")


@pytest.mark.parametrize(
    "rule, titles",
    [
        pytest.param(ec.Rule(id="rule", disabled=True), ["This rule is currently disabled and will not be applied"], id="disabled"),
        pytest.param(ec.Rule(id="rule", invert_matching=True), ["Matching is inverted in this rule"], id="inverted"),
        pytest.param(ec.Rule(id="rule", contact_groups=_ADMINS), [_CONTACT_GROUPS % "admins"], id="contact groups"),
        pytest.param(ec.Rule(id="rule", contact_groups=_NOBODY), [_CONTACT_GROUPS % "(none)"], id="no contact groups"),
    ],
)  # fmt: skip
@_setup_page
def test_rule_list_marks_special_rules(
    rule: ec.Rule,
    titles: Sequence[str],
    load_config: Config,
    test_edition: Edition,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    row = _listed_rule(rule, load_config, test_edition, mock_livestatus)

    assert _status_icon_titles(row) == titles


@_setup_page
def test_rule_list_shows_the_hits_of_each_rule_on_all_sites(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="hit")), _stored(ec.Rule(id="missed"))))

    with _rule_hit_queries(mock_livestatus, [(omd_site(), "hit", 2), ("remote", "hit", 3)]):
        rows = table_rows(_rule_list(load_config, test_edition), "Rules")

    assert [row["Hits"].get_text(strip=True) for row in rows] == ["5", "0"]


@pytest.mark.parametrize(
    "rule, title",
    [
        pytest.param(_MATCHING_RULE, "This rule matches.", id="match"),
        pytest.param(_CANCELLING_RULE, "This rule does a cancelling match.", id="cancel"),
        pytest.param(_DROPPING_RULE, "This rule matches and drops the message.", id="drop"),
        pytest.param(_SKIPPING_RULE, "This rule matches and skips the rest of this rule pack.", id="skip"),
        pytest.param(ec.Rule(id="groups", match="(nothing)"), "This rule matches. Match groups: nothing", id="match groups"),
        pytest.param(_NON_MATCHING_RULE, "Rule does not match: did not match, message text does not match", id="no match"),
    ],
)  # fmt: skip
@_setup_page
def test_rule_list_shows_how_the_simulated_event_matches_a_rule(
    rule: ec.Rule,
    title: str,
    load_config: Config,
    test_edition: Edition,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _fill_in_the_simulator()
    set_request_vars(_simulate="1")

    row = _listed_rule(rule, load_config, test_edition, mock_livestatus)

    assert _status_icon_titles(row) == [title]


_OVERRULED = "This rule matches, but is overruled by a previous match."


@_setup_page
def test_rule_list_shows_later_matches_of_the_simulated_event_as_overruled(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    _save_rule_packs(_rule_pack(_stored(_MATCHING_RULE), _stored(_DROPPING_RULE)))
    _fill_in_the_simulator()
    set_request_vars(_simulate="1")

    with _rule_hit_queries(mock_livestatus):
        rows = table_rows(_rule_list(load_config, test_edition), "Rules")

    assert [_status_icon_titles(row) for row in rows] == [["This rule matches."], [_OVERRULED]]


@_setup_page
def test_rule_list_shows_matches_of_the_simulated_event_overruled_by_a_previous_rule_pack(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    _save_rule_packs(
        _rule_pack(_stored(_MATCHING_RULE), rule_pack_id="previous"),
        _rule_pack(_stored(_MATCHING_RULE)),
    )
    _fill_in_the_simulator()
    set_request_vars(_simulate="1")

    with _rule_hit_queries(mock_livestatus):
        [row] = table_rows(_rule_list(load_config, test_edition), "Rules")

    assert _status_icon_titles(row) == [_OVERRULED]


def _rule_pack_editor(
    config: Config, edition: Edition
) -> mkeventd_wato.ModeEventConsoleEditRulePack:
    return _mode(mkeventd_wato.ModeEventConsoleEditRulePack, config, edition)


def _submit_rule_pack_form(config: Config, edition: Edition, **overrides: str) -> None:
    form = form_values(render_page(_rule_pack_editor(config, edition), config), "rule_pack")
    submit(**{**form, **overrides})


@_setup_page
def test_saving_a_new_rule_pack_puts_it_first(load_config: Config, test_edition: Edition) -> None:
    _save_rule_packs(_rule_pack(rule_pack_id="existing"))
    _submit_rule_pack_form(
        load_config, test_edition, rule_pack_p_id="new", rule_pack_p_title="New rule pack"
    )

    result = _rule_pack_editor(load_config, test_edition).action(load_config)

    assert _rule_pack_ids() == ["new", "existing"]
    assert redirect_vars(result) == {"mode": "mkeventd_rule_packs"}


@_setup_page
def test_saving_a_new_rule_pack_is_a_pending_change_of_the_event_console(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs()
    _submit_rule_pack_form(
        load_config, test_edition, rule_pack_p_id="new", rule_pack_p_title="New rule pack"
    )

    _rule_pack_editor(load_config, test_edition).action(load_config)

    assert _pending_changes() == [("new-rule-pack", [EVENT_CONSOLE])]


@_setup_page
def test_saving_a_rule_pack_with_the_id_of_another_one_is_refused(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(rule_pack_id="existing"))
    _submit_rule_pack_form(
        load_config, test_edition, rule_pack_p_id="existing", rule_pack_p_title="Duplicate"
    )

    with pytest.raises(MKUserError, match="A rule pack with this ID already exists."):
        _rule_pack_editor(load_config, test_edition).action(load_config)


@_setup_page
def test_saving_an_edited_rule_pack_keeps_its_rules(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="rule"))))
    set_request_vars(edit="0")
    _submit_rule_pack_form(load_config, test_edition, rule_pack_p_title="Renamed")

    _rule_pack_editor(load_config, test_edition).action(load_config)

    assert (_stored_rule_pack()["title"], _rule_ids()) == ("Renamed", ["rule"])


@_setup_page
def test_saving_an_edited_exported_rule_pack_updates_the_export(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_exported(_rule_pack()))
    set_request_vars(edit="0")
    _submit_rule_pack_form(load_config, test_edition, rule_pack_p_disabled="on")

    _rule_pack_editor(load_config, test_edition).action(load_config)

    assert _stored_rule_pack()["disabled"] is True


@_setup_page
def test_the_id_and_title_of_an_exported_rule_pack_are_fixed(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_exported(_rule_pack()))
    set_request_vars(edit="0")

    form = form_values(
        render_page(_rule_pack_editor(load_config, test_edition), load_config), "rule_pack"
    )

    assert {"rule_pack_p_id", "rule_pack_p_title"}.isdisjoint(form)


@_setup_page
def test_editing_an_unknown_rule_pack_is_refused(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack())
    set_request_vars(edit="1")

    with pytest.raises(MKUserError, match="The rule pack you are trying to edit does not exist."):
        _rule_pack_editor(load_config, test_edition)


@pytest.mark.parametrize(
    "variables, title",
    [
        pytest.param({}, "Add rule pack", id="new"),
        pytest.param({"edit": "0"}, "Edit rule pack pack", id="edit"),
    ],
)
@_setup_page
def test_rule_pack_editor_title_says_whether_it_adds_or_edits(
    variables: Mapping[str, str], title: str, load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack())
    set_request_vars(**variables)

    assert _rule_pack_editor(load_config, test_edition).title() == title


def _rule_editor(config: Config, edition: Edition) -> mkeventd_wato.ModeEventConsoleEditRule:
    return _mode(mkeventd_wato.ModeEventConsoleEditRule, config, edition)


def _submit_rule_form(config: Config, edition: Edition, **overrides: str) -> None:
    form = form_values(render_page(_rule_editor(config, edition), config), "rule")
    submit(**{**form, **overrides})


def _rule_descriptions(rule_pack_id: str = "pack") -> list[str | None]:
    return [rule.get("description") for rule in _stored_rule_pack(rule_pack_id)["rules"]]


@_setup_page
def test_saving_a_new_rule_puts_it_first_in_its_rule_pack(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="existing"))))
    set_request_vars(rule_pack="pack")
    _submit_rule_form(load_config, test_edition, rule_p_id="new")

    result = _rule_editor(load_config, test_edition).action(load_config)

    assert _rule_ids() == ["new", "existing"]
    assert redirect_vars(result) == {"mode": "mkeventd_rules", "rule_pack": "pack"}


@_setup_page
def test_saving_a_clone_inserts_it_before_the_original(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="first")), _stored(ec.Rule(id="second"))))
    set_request_vars(rule_pack="pack", clone="1")
    _submit_rule_form(load_config, test_edition, rule_p_id="clone")

    _rule_editor(load_config, test_edition).action(load_config)

    assert _rule_ids() == ["first", "clone", "second"]


@_setup_page
def test_saving_a_new_rule_of_an_exported_rule_pack_updates_the_export(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_exported(_rule_pack(_stored(ec.Rule(id="existing")))))
    set_request_vars(rule_pack="pack")
    _submit_rule_form(load_config, test_edition, rule_p_id="new")

    _rule_editor(load_config, test_edition).action(load_config)

    assert _rule_ids() == ["new", "existing"]


@_setup_page
def test_saving_an_edited_rule_replaces_it(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="first")), _stored(ec.Rule(id="second"))))
    set_request_vars(rule_pack="pack", edit="1")
    _submit_rule_form(load_config, test_edition, rule_p_description="edited")
    mock_livestatus.expect_query("COMMAND [...] EC_RESETCOUNTERS;second", match_type="ellipsis")

    with mock_livestatus(expect_status_query=True):
        _rule_editor(load_config, test_edition).action(load_config)

    assert _rule_descriptions() == [None, "edited"]


@_setup_page
def test_saving_an_edited_rule_resets_its_hit_counters_in_the_local_event_console(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="rule"))))
    set_request_vars(rule_pack="pack", edit="0")
    _submit_rule_form(load_config, test_edition)
    mock_livestatus.expect_query(
        "COMMAND [...] EC_RESETCOUNTERS;rule", match_type="ellipsis", sites=[omd_site()]
    )

    with mock_livestatus(expect_status_query=True):
        _rule_editor(load_config, test_edition).action(load_config)


@_setup_page
def test_changing_the_id_of_an_existing_rule_is_refused(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="rule"))))
    set_request_vars(rule_pack="pack", edit="0")
    _submit_rule_form(load_config, test_edition, rule_p_id="renamed")

    with pytest.raises(
        MKUserError, match="It is not allowed to change the ID of an existing rule."
    ):
        _rule_editor(load_config, test_edition).action(load_config)


@_setup_page
def test_saving_a_new_rule_with_the_id_of_a_rule_in_another_rule_pack_is_refused(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="taken")), rule_pack_id="other"), _rule_pack())
    set_request_vars(rule_pack="pack")
    _submit_rule_form(load_config, test_edition, rule_p_id="taken")

    with pytest.raises(
        MKUserError, match="A rule with this ID already exists in rule pack <b>Other</b>."
    ):
        _rule_editor(load_config, test_edition).action(load_config)


@pytest.mark.parametrize(
    "settings, error",
    [
        pytest.param({"rule_p_match": "(("}, "Invalid regular expression", id="invalid pattern"),
        pytest.param({"rule_p_match": 10 * "(a)"}, "Only nine are allowed.", id="too many groups"),
        pytest.param({"rule_p_match": "(a)", "rule_p_set_text_USE": "on", "rule_p_set_text": "\\2"}, "but your match text has only 1 subgroups", id="missing group"),
        pytest.param({"rule_p_count_USE": "on", "rule_p_expect_USE": "on", "rule_p_expect_p_count": "1"}, "You cannot use counting and expecting", id="count and expect"),
        pytest.param({"rule_p_expect_USE": "on", "rule_p_expect_p_count": "1", "rule_p_delay_USE": "on"}, "You cannot use expecting and delay", id="expect and delay"),
    ],
)  # fmt: skip
@_setup_page
def test_saving_a_rule_with_invalid_settings_is_refused(
    settings: Mapping[str, str], error: str, load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack())
    set_request_vars(rule_pack="pack")
    _submit_rule_form(load_config, test_edition, rule_p_id="new", **settings)

    with pytest.raises(MKUserError, match=error):
        _rule_editor(load_config, test_edition).action(load_config)


# Compiling the questionable pattern anyway warns again, with the warning of Python itself.
@pytest.mark.filterwarnings("ignore:Possible nested set at position 1$:FutureWarning")
@_setup_page
def test_saving_a_rule_with_a_questionable_pattern_warns_about_it(
    load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack())
    set_request_vars(rule_pack="pack")
    # Python's regular expressions might give this a different meaning in the future.
    _submit_rule_form(load_config, test_edition, rule_p_id="new", rule_p_match="[[a]")

    with pytest.warns(RegexFutureWarning, match=r"Possible nested set .* in \[\[a\]"):
        _rule_editor(load_config, test_edition).action(load_config)

    assert _rule_ids() == ["new"]


@_setup_page
def test_rule_editor_finds_the_rule_pack_of_a_rule_given_by_its_id(
    load_config: Config, test_edition: Edition
) -> None:
    # Links from the event views only know the ID of the rule.
    _save_rule_packs(
        _rule_pack(_stored(ec.Rule(id="other")), rule_pack_id="other"),
        _rule_pack(_stored(ec.Rule(id="first")), _stored(ec.Rule(id="second"))),
    )
    set_request_vars(rule_id="second")

    editor = _rule_editor(load_config, test_edition)

    assert (editor.title(), request.var("rule_pack"), request.var("edit")) == (
        "Edit rule second",
        "pack",
        "1",
    )


@pytest.mark.parametrize(
    "variables, field",
    [
        pytest.param({"rule_id": "unknown"}, "rule_id", id="by ID"),
        pytest.param({"rule_pack": "pack", "edit": "1"}, "edit", id="by number"),
    ],
)
@_setup_page
def test_editing_an_unknown_rule_is_refused(
    variables: Mapping[str, str], field: str, load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="rule"))))
    set_request_vars(**variables)

    with pytest.raises(MKUserError, match="The rule you are trying to edit does not exist.") as e:
        _rule_editor(load_config, test_edition)

    assert e.value.varname == field


@pytest.mark.parametrize(
    "variables, title",
    [
        pytest.param({}, "Add rule", id="new"),
        pytest.param({"clone": "0"}, "Add rule", id="clone"),
        pytest.param({"edit": "0"}, "Edit rule rule", id="edit"),
    ],
)
@_setup_page
def test_rule_editor_title_says_whether_it_adds_or_edits(
    variables: Mapping[str, str], title: str, load_config: Config, test_edition: Edition
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="rule"))))
    set_request_vars(rule_pack="pack", **variables)

    assert _rule_editor(load_config, test_edition).title() == title


def _start_event_daemon() -> None:
    """Makes the local event daemon look like it is running, without answering on its socket"""
    socket_path = cmk.utils.paths.omd_root / "tmp/run/mkeventd/status"
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.touch()


def _status_page(
    config: Config,
    edition: Edition,
    live: MockLiveStatusConnection,
    status: Mapping[str, object] | None,
) -> str:
    _start_event_daemon()
    with _local_event_console(live, status):
        return render_page(_mode(mkeventd_wato.ModeEventConsoleStatus, config, edition), config)


@_setup_page
def test_status_page_without_a_running_event_daemon_says_so(
    load_config: Config, test_edition: Edition
) -> None:
    page = render_page(
        _mode(mkeventd_wato.ModeEventConsoleStatus, load_config, test_edition), load_config
    )

    assert "The Event Console daemon is currently not running." in page


@_setup_page
def test_status_page_of_an_event_daemon_without_a_status_says_it_is_not_running(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    page = _status_page(load_config, test_edition, mock_livestatus, None)

    assert "The Event Console daemon is currently not running." in page


@pytest.mark.parametrize(
    "replication_mode, text",
    [
        pytest.param("", "central / standalone", id="central"),
        pytest.param("sync", "synchronize", id="sync"),
        pytest.param("takeover", "Takeover!", id="takeover"),
    ],
)
@_setup_page
def test_status_page_shows_the_replication_mode(
    replication_mode: str,
    text: str,
    load_config: Config,
    test_edition: Edition,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    page = _status_page(
        load_config, test_edition, mock_livestatus, _event_console_status(replication_mode)
    )

    assert f"Current replication mode: <b>{text}</b>" in page


@pytest.mark.parametrize(
    "success, text",
    [
        pytest.param(1, "Success", id="success"),
        pytest.param(0, "Failed!", id="failure"),
    ],
)
@_setup_page
def test_status_page_shows_the_result_of_the_last_replication(
    success: int,
    text: str,
    load_config: Config,
    test_edition: Edition,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    page = _status_page(
        load_config, test_edition, mock_livestatus, _event_console_status("sync", success=success)
    )

    assert f"Status of last synchronization: <b>{text}</b>" in page


@time_machine.travel(datetime.fromtimestamp(1622638021, tz=UTC), tick=False)
@_setup_page
def test_status_page_shows_how_long_ago_the_replication_last_succeeded(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    status = _event_console_status("sync", last_sync=time.time() - 42)

    page = _status_page(load_config, test_edition, mock_livestatus, status)

    assert "Last successful sync 42 seconds ago." in page


@_setup_page
def test_status_page_shows_that_the_replication_never_succeeded(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    status = _event_console_status("sync", success=0, last_sync=0)

    page = _status_page(load_config, test_edition, mock_livestatus, status)

    assert "No successful synchronization so far." in page


@pytest.mark.parametrize(
    "replication_mode, button",
    [
        pytest.param("sync", "_switch_takeover", id="sync"),
        pytest.param("takeover", "_switch_sync", id="takeover"),
    ],
)
@_setup_page
def test_status_page_offers_to_switch_the_replication_mode(
    replication_mode: str,
    button: str,
    load_config: Config,
    test_edition: Edition,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    page = _status_page(
        load_config, test_edition, mock_livestatus, _event_console_status(replication_mode)
    )

    assert f'name="{button}"' in page


@pytest.mark.parametrize(
    "button, replication_mode",
    [
        pytest.param("_switch_sync", "sync", id="sync"),
        pytest.param("_switch_takeover", "takeover", id="takeover"),
    ],
)
@_setup_page
def test_switching_the_replication_mode_switches_the_local_event_console(
    button: str,
    replication_mode: str,
    load_config: Config,
    test_edition: Edition,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    submit(**{button: "1"})
    mock_livestatus.expect_query(
        f"COMMAND [...] EC_SWITCH_MODE;{replication_mode}",
        match_type="ellipsis",
        sites=[omd_site()],
    )

    with mock_livestatus(expect_status_query=True):
        _mode(mkeventd_wato.ModeEventConsoleStatus, load_config, test_edition).action(load_config)


@pytest.mark.usefixtures("request_context", "with_user_login", "patch_theme")
def test_switching_the_replication_mode_needs_the_permission_for_it(
    load_config: Config, test_edition: Edition, mock_livestatus: MockLiveStatusConnection
) -> None:
    submit(_switch_takeover="1")

    with mock_livestatus(expect_status_query=False):
        _mode(mkeventd_wato.ModeEventConsoleStatus, load_config, test_edition).action(load_config)

    assert _flashed_messages() == []


_SELF_CONTAINED_MIB = """TEST-MIB DEFINITIONS ::= BEGIN
testRoot OBJECT IDENTIFIER ::= { iso 3 6 1 4 1 99999 }
END
"""


def _custom_mib(file_name: str, content: str = _SELF_CONTAINED_MIB) -> None:
    path = _paths().local_mibs_dir.value / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _custom_mibs() -> list[str]:
    return sorted(path.name for path in _paths().local_mibs_dir.value.glob("*"))


def _mib_list_action(config: Config, edition: Edition) -> ActionResult:
    return _mode(mkeventd_wato.ModeEventConsoleMIBs, config, edition).action(config)


@_setup_page
def test_mib_list_shows_the_name_and_organization_of_the_custom_mibs(
    load_config: Config, test_edition: Edition
) -> None:
    _custom_mib(
        "test.mib",
        "TEST-MIB DEFINITIONS ::= BEGIN\n"
        "testMib MODULE-IDENTITY\n"
        '    ORGANIZATION "Example Inc."\n'
        "    ::= { iso 3 6 1 4 1 99999 }\n"
        "testRoot OBJECT IDENTIFIER ::= { testMib 1 }\n"
        "END\n",
    )

    [row] = table_rows(
        render_page(
            _mode(mkeventd_wato.ModeEventConsoleMIBs, load_config, test_edition), load_config
        ),
        "Custom MIBs",
    )

    assert (
        row["File name"].get_text(),
        row["MIB"].get_text(),
        row["Organization"].get_text(),
    ) == ("test.mib", "TEST-MIB", "Example Inc.")


@_setup_page
def test_deleting_a_custom_mib_removes_it_and_its_compiled_module(
    load_config: Config, test_edition: Edition
) -> None:
    _custom_mib("test.mib")
    compiled_mib = _paths().compiled_mibs_dir.value / "TEST-MIB.py"
    compiled_mib.parent.mkdir(parents=True, exist_ok=True)
    compiled_mib.touch()
    submit(_delete="test.mib")

    result = _mib_list_action(load_config, test_edition)

    assert (_custom_mibs(), compiled_mib.exists()) == ([], False)
    assert redirect_vars(result) == {"mode": "mkeventd_mibs"}


@_setup_page
def test_deleting_a_mib_which_is_no_custom_one_is_ignored(
    load_config: Config, test_edition: Edition
) -> None:
    shipped_mib = _paths().checkmk_mibs_dir.value / "SHIPPED-MIB.txt"
    shipped_mib.parent.mkdir(parents=True, exist_ok=True)
    shipped_mib.write_text(_SELF_CONTAINED_MIB)
    submit(_delete="../../../../share/snmp/mibs/SHIPPED-MIB.txt")

    _mib_list_action(load_config, test_edition)

    assert shipped_mib.exists()


@_setup_page
def test_bulk_deleting_custom_mibs_removes_the_selected_ones(
    load_config: Config, test_edition: Edition
) -> None:
    _custom_mib("first.mib")
    _custom_mib("second.mib")
    _custom_mib("third.mib")
    submit(**{"_bulk_delete_custom_mibs": "1", "_c_mib_first.mib": "on", "_c_mib_third.mib": "on"})

    _mib_list_action(load_config, test_edition)

    assert _custom_mibs() == ["second.mib"]


def _upload(app: WebTestAppForCMK, file_name: str, content: bytes) -> CmkTestResponse:
    """Uploads the file with the form of the upload page, like a browser"""
    url = "/NO_SITE/check_mk/wato.py?mode=mkeventd_upload_mibs"
    form = form_values(app.get(url).text, "upload_form")
    upload = (io.BytesIO(content), file_name, "text/plain")
    return app.post(url, data={**form, "_save": "1", "_upload_mib": upload})


@pytest.mark.parametrize(
    "file_name, content, error",
    [
        pytest.param("empty.txt", b" \n", "The file is empty", id="empty"),
        pytest.param(".hidden.txt", _SELF_CONTAINED_MIB.encode(), "Invalid file name", id="hidden"),
        pytest.param("mibs.tar.gz", b"no tar file", "Sorry, uploading TAR/GZ files is not yet implemented.", id="tar"),
    ],
)  # fmt: skip
@pytest.mark.usefixtures("patch_theme")
def test_uploading_something_which_is_no_mib_is_refused(
    file_name: str, content: bytes, error: str, logged_in_admin_wsgi_app: WebTestAppForCMK
) -> None:
    response = _upload(logged_in_admin_wsgi_app, file_name, content)

    assert error_messages(response.text) == [error]


def _related_pages(mode: mkeventd_wato.ABCEventConsoleMode, config: Config) -> list[str]:
    [related] = [
        dropdown
        for dropdown in mode.page_menu(config, Breadcrumb()).dropdowns
        if dropdown.name == "related"
    ]
    return [entry.title for topic in related.topics for entry in topic.entries]


@pytest.mark.parametrize(
    "mode_class, pages",
    [
        pytest.param(mkeventd_wato.ModeEventConsoleStatus, ["Rule packs", "Rules", "Settings", "SNMP MIBs"], id="status"),
        pytest.param(mkeventd_wato.ModeEventConsoleMIBs, ["Rule packs", "Rules", "Status", "Settings"], id="MIBs"),
    ],
)  # fmt: skip
@_setup_page
def test_related_pages_are_the_other_event_console_pages(
    mode_class: type[mkeventd_wato.ABCEventConsoleMode],
    pages: Sequence[str],
    load_config: Config,
    test_edition: Edition,
) -> None:
    assert _related_pages(_mode(mode_class, load_config, test_edition), load_config) == pages


@pytest.mark.usefixtures("request_context", "with_user_login", "patch_theme")
def test_related_pages_need_the_configuration_permission_for_the_settings_and_rules(
    load_config: Config, test_edition: Edition
) -> None:
    mode = _mode(mkeventd_wato.ModeEventConsoleStatus, load_config, test_edition)

    assert _related_pages(mode, load_config) == ["Rule packs", "SNMP MIBs"]


@pytest.mark.parametrize(
    "mode_class, variables",
    [
        pytest.param(mkeventd_wato.ModeEventConsoleRulePacks, {}, id="rule packs"),
        pytest.param(mkeventd_wato.ModeEventConsoleRules, {"rule_pack": "pack"}, id="rules"),
        pytest.param(mkeventd_wato.ModeEventConsoleEditRulePack, {}, id="rule pack editor"),
        pytest.param(
            mkeventd_wato.ModeEventConsoleEditRule, {"rule_pack": "pack"}, id="rule editor"
        ),
        pytest.param(mkeventd_wato.ModeEventConsoleStatus, {}, id="status"),
        pytest.param(mkeventd_wato.ModeEventConsoleMIBs, {}, id="MIBs"),
        pytest.param(mkeventd_wato.ModeEventConsoleUploadMIBs, {}, id="MIB upload"),
    ],
)
@_setup_page
def test_a_disabled_event_console_refuses_its_setup_pages(
    mode_class: type[mkeventd_wato.ABCEventConsoleMode],
    variables: Mapping[str, str],
    load_config: Config,
    test_edition: Edition,
) -> None:
    _save_rule_packs(_rule_pack())
    set_request_vars(**variables)
    mode = _mode(mode_class, load_config, test_edition)

    with pytest.raises(MKUserError, match="The Event Console is disabled"):
        render_page(mode, dataclasses.replace(load_config, mkeventd_enabled=False))


def _notification_configuration() -> Path:
    return cmk.utils.paths.nagios_conf_dir / "mkeventd_notifications.cfg"


@pytest.mark.usefixtures("request_context")
def test_notifications_of_the_configured_contact_group_go_to_the_event_console(
    set_config: SetConfig,
) -> None:
    with set_config(mkeventd_notify_contactgroup="admins"):
        mkeventd_wato.mkeventd_update_notification_configuration({})

    assert ["contactgroups", "admins"] in [
        line.split() for line in _notification_configuration().read_text().splitlines()
    ]


@pytest.mark.usefixtures("request_context")
def test_notifications_go_to_the_configured_remote_event_console_with_the_configured_facility(
    set_config: SetConfig,
) -> None:
    with set_config(
        mkeventd_notify_contactgroup="admins",
        mkeventd_notify_remotehost="10.1.2.3",
        mkeventd_notify_facility=20,
    ):
        mkeventd_wato.mkeventd_update_notification_configuration({})

    assert "command_line                   mkevent -n 20 '10.1.2.3' " in (
        _notification_configuration().read_text()
    )


@pytest.mark.usefixtures("request_context")
def test_without_a_contact_group_no_notifications_go_to_the_event_console(
    set_config: SetConfig,
) -> None:
    with set_config(mkeventd_notify_contactgroup="admins"):
        mkeventd_wato.mkeventd_update_notification_configuration({})

    with set_config(mkeventd_notify_contactgroup=""):
        mkeventd_wato.mkeventd_update_notification_configuration({})

    assert not _notification_configuration().exists()


def _validation_errors(config_variable: ConfigVariable, value: object) -> list[str]:
    context = GlobalSettingsContext(
        target_site_id=omd_site(),
        edition_of_local_site=Edition.COMMUNITY,
        site_neutral_log_dir=cmk.utils.paths.log_dir,
        site_neutral_var_dir=cmk.utils.paths.var_dir,
        configured_sites=SiteConfigurations({}),
        configured_graph_timeranges=[],
        folder_choices=lambda: [("", "Main")],
    )
    visitor = get_visitor(
        config_variable.value_model(context), VisitorOptions(migrate_values=True, mask_values=False)
    )
    return [error.message for error in visitor.validate(RawDiskData(value))]


def _email_action(action_id: str) -> Mapping[str, object]:
    return {
        "id": action_id,
        "title": action_id.title(),
        "disabled": False,
        "hidden": False,
        "action": ("email", {"to": "admin@example.com", "subject": "Event", "body": ""}),
    }


_MISSING_MAIL = "You are missing the action with the ID mail, which is still used in some rules."


@pytest.mark.parametrize(
    "used_action, configured_actions, errors",
    [
        pytest.param("mail", [], [_MISSING_MAIL], id="missing"),
        pytest.param("mail", [_email_action("mail")], [], id="configured"),
        pytest.param("@NOTIFY", [], [], id="built-in"),
    ],
)
@pytest.mark.usefixtures("patch_omd_site")
def test_actions_used_by_rules_cannot_be_removed(
    used_action: str, configured_actions: Sequence[Mapping[str, object]], errors: Sequence[str]
) -> None:
    _save_rule_packs(_rule_pack(_stored(ec.Rule(id="rule", actions=[used_action]))))

    assert (
        _validation_errors(mkeventd_wato.ConfigVariableEventConsoleActions, configured_actions)
        == errors
    )


def test_a_hostname_translation_with_a_single_regular_expression_from_before_1_4_is_valid() -> None:
    assert (
        _validation_errors(
            mkeventd_wato.ConfigVariableHostnameTranslation, {"regex": ("(.*)\\.example", "\\1")}
        )
        == []
    )
