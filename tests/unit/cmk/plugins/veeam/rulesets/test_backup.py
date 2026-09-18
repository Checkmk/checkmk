#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.veeam.agent_based.veeam_client import check_plugin_veeam_client
from cmk.plugins.veeam.rulesets.backup import rule_spec_veeam_backup


@pytest.fixture
def _register_form_spec_visitors() -> None:
    registration.register()


@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_a_legacy_tuple_rule_migrates_to_simple_levels() -> None:
    # 2.4/2.5 rules stored a bare (warn, crit) tuple under "age"; the form spec
    # migrates it on load, the same way the GUI does at runtime.
    visitor = get_visitor(
        rule_spec_veeam_backup.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    stored = RawDiskData({"age": (108000, 172800)})

    assert visitor.validate(stored) == []
    assert visitor.to_disk(stored) == {"age": ("fixed", (108000.0, 172800.0))}


@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_an_empty_rule_stays_valid() -> None:
    # "age" is optional; the check falls back to its default levels. The shipped
    # sample rules store an empty dictionary and rely on this.
    visitor = get_visitor(
        rule_spec_veeam_backup.parameter_form(),
        VisitorOptions(migrate_values=False, mask_values=False),
    )

    assert visitor.validate(RawDiskData({})) == []


@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_the_shipped_default_needs_no_migration() -> None:
    # Mirrors the config_anonymizer gate: with migrate_values=False the stored
    # value must already be in the tagged shape.
    defaults = check_plugin_veeam_client.check_default_parameters
    assert defaults is not None

    visitor = get_visitor(
        rule_spec_veeam_backup.parameter_form(),
        VisitorOptions(migrate_values=False, mask_values=False),
    )

    assert visitor.validate(RawDiskData(dict(defaults))) == []
