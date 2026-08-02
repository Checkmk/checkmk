#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.wato._check_mk_configuration import (
    _migrate_log_levels,
    _migrate_piggybacked_host_files,
    ConfigVariableChooseSNMPBackend,
    make_snmp_backend_hosts_rulespec,
)
from cmk.gui.watolib.config_domain_name import GlobalSettingsContext
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.v1.form_specs import FormSpec


@pytest.mark.parametrize(
    ("rule_value", "expected_result"),
    [
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [
                            ("exact_match", "some-host"),
                            ("regular_expression", "test.*"),
                        ],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [
                            ("exact_match", "some-host"),
                            ("regular_expression", "test.*"),
                        ],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            id="up-to-date format",
        ),
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "piggybacked_hostname_expressions": ["valid"],
                        "max_cache_age": "global",
                        "validity": {"period": 60, "check_mk_state": 0},
                    },
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [("exact_match", "valid")],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            id="legacy format with valid host name",
        ),
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "piggybacked_hostname_expressions": ["~test.*"],
                        "max_cache_age": "global",
                        "validity": {"period": 60, "check_mk_state": 0},
                    },
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "max_cache_age": "global",
                        "piggybacked_hostname_conditions": [("regular_expression", "test.*")],
                        "validity": {"check_mk_state": 0, "period": 60},
                    },
                ],
            },
            id="legacy format with regular expression",
        ),
        pytest.param(
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [
                    {
                        "piggybacked_hostname_expressions": ["^test$", "^test2.*"],
                        "max_cache_age": "global",
                        "validity": {"period": 60, "check_mk_state": 0},
                    }
                ],
            },
            {
                "global_max_cache_age": "global",
                "global_validity": {"period": 60, "check_mk_state": 0},
                "per_piggybacked_host": [],
            },
            id="legacy format with invalid host names",
        ),
    ],
)
def test_migrate_piggybacked_host_files(
    rule_value: Mapping[str, object],
    expected_result: Mapping[str, object],
) -> None:
    assert _migrate_piggybacked_host_files(rule_value) == expected_result


@pytest.mark.parametrize(
    ("params", "expected_result"),
    [
        pytest.param(
            {"cmk.web": 30, "cmk.web.automations": 10},
            {"cmk.web": 30, "cmk.automations": 10},
            id="CMK-36979: rename carries the configured level over",
        ),
        pytest.param(
            # An already-migrated value wins; the stale key is dropped.
            {"cmk.automations": 10, "cmk.web.automations": 20},
            {"cmk.automations": 10},
            id="CMK-36979: existing new key is not clobbered",
        ),
        pytest.param(
            {"cmk.web": 30, "cmk.automations": 10},
            {"cmk.web": 30, "cmk.automations": 10},
            id="already migrated is unchanged",
        ),
    ],
)
def test_migrate_log_levels(
    params: dict[str, int],
    expected_result: dict[str, int],
) -> None:
    assert _migrate_log_levels(params) == expected_result


def _global_settings_context(edition: Edition) -> GlobalSettingsContext:
    return GlobalSettingsContext(
        target_site_id=SiteId("mysite"),
        edition_of_local_site=edition,
        site_neutral_log_dir=Path("/omd/sites/mysite/var/log"),
        site_neutral_var_dir=Path("/omd/sites/mysite/var"),
        configured_sites=SiteConfigurations({}),
        configured_graph_timeranges=[],
    )


def _validate_snmp_backend_default(edition: Edition, backend: str) -> Sequence[object]:
    """Validate a value of the global setting as if it came from the config file"""
    value_model = ConfigVariableChooseSNMPBackend.value_model(_global_settings_context(edition))
    assert isinstance(value_model, FormSpec)
    return get_visitor(
        value_model, VisitorOptions(migrate_values=True, mask_values=False)
    ).validate(RawDiskData(backend))


@pytest.mark.parametrize("backend", ["classic", "inline"])
def test_snmp_backend_available_in_pro(backend: str) -> None:
    assert not _validate_snmp_backend_default(Edition.PRO, backend)
    make_snmp_backend_hosts_rulespec(Edition.PRO).valuespec.validate_value(backend, "varprefix")


def test_classic_snmp_backend_available_in_community() -> None:
    assert not _validate_snmp_backend_default(Edition.COMMUNITY, "classic")
    make_snmp_backend_hosts_rulespec(Edition.COMMUNITY).valuespec.validate_value(
        "classic", "varprefix"
    )


def test_inline_snmp_backend_unavailable_in_community() -> None:
    """A value left over from a downgrade must be rejected, not silently accepted"""
    assert _validate_snmp_backend_default(Edition.COMMUNITY, "inline")
    with pytest.raises(MKUserError):
        make_snmp_backend_hosts_rulespec(Edition.COMMUNITY).valuespec.validate_value(
            "inline", "varprefix"
        )
