#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec
from cmk.gui.watolib.rulespecs import Rulespec
from cmk.plugins.cisco_meraki.rulesets.agent_cisco_meraki import (
    _check_for_duplicates,
    _migrate_to_valid_ident,
    rule_spec_cisco_meraki,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError


class TestMigrateToValidIdent:
    def test_good_input(self) -> None:
        value = _migrate_to_valid_ident(["licenses-overview", "nodelimeter"])
        expected = ["licenses_overview", "nodelimeter"]
        assert value == expected

    def test_no_input(self) -> None:
        assert _migrate_to_valid_ident([]) == []

    def test_non_string_values_are_ignored(self) -> None:
        assert _migrate_to_valid_ident([1, 2, 3]) == []

    def test_bad_input_raises(self) -> None:
        with pytest.raises(ValueError):
            _migrate_to_valid_ident("licenses-overview")


class TestCheckForDuplicates:
    def test_good_input(self) -> None:
        _check_for_duplicates(["abc", "dfe"])

    def test_no_input(self) -> None:
        _check_for_duplicates([])

    def test_bad_input_raises(self) -> None:
        with pytest.raises(ValidationError):
            _check_for_duplicates(["abc", "abc"])


class TestLegacyProxyMigration:
    @pytest.fixture
    def rule(self) -> Rulespec:
        return convert_to_legacy_rulespec(rule_spec_cisco_meraki, Edition.COMMUNITY, lambda x: x)

    @pytest.fixture
    def payload(self) -> dict[str, object]:
        return {"api_key": ("password", "test-password")}

    def test_no_legacy_proxy(self, rule: Rulespec, payload: dict[str, object]) -> None:
        payload["proxy"] = ("no_proxy", None)
        rule.valuespec.validate_datatype(payload, "")
        rule.valuespec.validate_value(payload, "")

    def test_with_legacy_proxy(self, rule: Rulespec, payload: dict[str, object]) -> None:
        payload["proxy"] = ("url", "https://example.com")
        rule.valuespec.validate_datatype(payload, "")
        rule.valuespec.validate_value(payload, "")
