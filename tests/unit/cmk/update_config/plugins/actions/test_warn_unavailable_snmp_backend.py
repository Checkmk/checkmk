#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence

import pytest

from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.watolib.config_domains import ConfigDomainCACertificates
from cmk.gui.watolib.global_settings import save_global_settings
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import HostRulespec
from cmk.livestatus_client import NetworkSocketDetails, SiteConfiguration, SiteConfigurations
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions import warn_unavailable_snmp_backend as action_module
from cmk.update_config.plugins.actions.warn_unavailable_snmp_backend import (
    warn_unavailable_snmp_backend,
    WarnUnavailableSNMPBackend,
)
from cmk.utils import paths

LOGGER = logging.getLogger("test")

_RULESET_NAME = "snmp_backend_hosts"


def _rulesets(rule_values: Sequence[object]) -> RulesetCollection:
    ruleset = Ruleset(
        _RULESET_NAME,
        rulespec=HostRulespec(
            name=_RULESET_NAME,
            group=RulespecGroupMonitoringConfigurationVarious,
            valuespec=lambda: DropdownChoice(
                choices=[("classic", "classic"), ("inline", "inline")]
            ),
        ),
    )
    folder = folder_tree().root_folder()
    for value in rule_values:
        rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
        rule.value = value
        ruleset.append_rule(folder, rule)
    return RulesetCollection({_RULESET_NAME: ruleset})


@pytest.mark.usefixtures("request_context")
def test_warns_about_globally_configured_inline_backend(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_unavailable_snmp_backend(
            Edition.COMMUNITY,
            {"snmp_backend_default": "inline"},
            SiteConfigurations({}),
            _rulesets([]),
            LOGGER,
        )

    assert "Choose SNMP backend" in caplog.text


@pytest.mark.usefixtures("request_context")
def test_warns_about_inline_backend_rules(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_unavailable_snmp_backend(
            Edition.COMMUNITY,
            {},
            SiteConfigurations({}),
            _rulesets(["inline", "classic"]),
            LOGGER,
        )

    assert "1 rule of" in caplog.text


@pytest.mark.usefixtures("request_context")
def test_warns_about_multiple_inline_backend_rules(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_unavailable_snmp_backend(
            Edition.COMMUNITY,
            {},
            SiteConfigurations({}),
            _rulesets(["inline", "inline"]),
            LOGGER,
        )

    assert "2 rules of" in caplog.text


def _sites_with_globals(site_globals: dict[str, object]) -> SiteConfigurations:
    """A replicating remote site, so that its site specific globals are editable"""
    site = SiteConfiguration(
        id=SiteId("remote"),
        alias="Remote",
        socket=(
            "tcp",
            NetworkSocketDetails(
                address=("127.0.0.1", 6557),
                tls=("encrypted", {"verify": True}),
            ),
        ),
        disable_wato=True,
        disabled=False,
        insecure=False,
        url_prefix="/remote/",
        multisiteurl="http://remote/check_mk/",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave",
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
        globals=site_globals,
    )
    return SiteConfigurations({SiteId("remote"): site})


@pytest.mark.usefixtures("request_context")
def test_warns_about_inline_backend_in_site_globals(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_unavailable_snmp_backend(
            Edition.COMMUNITY,
            {},
            _sites_with_globals({"snmp_backend_default": "inline"}),
            _rulesets([]),
            LOGGER,
        )

    assert "site specific global settings of site 'remote'" in caplog.text


@pytest.mark.usefixtures("request_context")
def test_silent_without_inline_backend_in_site_globals(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_unavailable_snmp_backend(
            Edition.COMMUNITY,
            {},
            _sites_with_globals({"snmp_backend_default": "classic"}),
            _rulesets([]),
            LOGGER,
        )

    assert not caplog.text


@pytest.mark.usefixtures("request_context")
def test_silent_without_inline_backend(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_unavailable_snmp_backend(
            Edition.COMMUNITY,
            {"snmp_backend_default": "classic"},
            SiteConfigurations({}),
            _rulesets(["classic"]),
            LOGGER,
        )

    assert not caplog.text


@pytest.mark.usefixtures("request_context")
def test_silent_in_editions_shipping_the_inline_backend(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_unavailable_snmp_backend(
            Edition.PRO,
            {"snmp_backend_default": "inline"},
            SiteConfigurations({}),
            _rulesets(["inline"]),
            LOGGER,
        )

    assert not caplog.text


def _action() -> WarnUnavailableSNMPBackend:
    return WarnUnavailableSNMPBackend(
        name="warn_unavailable_snmp_backend",
        title="Checking for an unavailable SNMP backend",
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_310,
    )


def _configure_inline_backend() -> None:
    save_global_settings(
        {**ConfigDomainCACertificates().default_globals(), "snmp_backend_default": "inline"}
    )


@pytest.mark.usefixtures("request_context")
def test_action_warns_on_the_central_site(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(action_module, "edition", lambda _omd_root: Edition.COMMUNITY)
    _configure_inline_backend()

    with caplog.at_level(logging.WARNING):
        _action()(LOGGER)

    assert "Choose SNMP backend" in caplog.text


@pytest.mark.usefixtures("request_context")
def test_action_is_silent_on_remote_sites(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The central site owns the configuration, warning here would not help anybody"""
    monkeypatch.setattr(action_module, "edition", lambda _omd_root: Edition.COMMUNITY)
    _configure_inline_backend()
    (paths.check_mk_config_dir / "distributed_wato.mk").write_text(
        "is_distributed_setup_remote_site = True\n"
    )

    with caplog.at_level(logging.WARNING):
        _action()(LOGGER)

    assert not caplog.text
