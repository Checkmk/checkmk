#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.cisco_meraki.rulesets.agent_cisco_meraki import _migrate_to_valid_ident


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
