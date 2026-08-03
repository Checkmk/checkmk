#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""Tests for `Ruleset.format_raw_value`'s self-bootstrapping output.

The emitted `rules.mk` source must load against an empty exec context
(`default={}`) without requiring callers to pre-seed the parent dict for
bundled rulespecs.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from cmk.ccc.store import load_mk_file
from cmk.gui.watolib.rulesets import Ruleset
from cmk.ruleset_matcher.matcher import RuleSpec


def _rule(rule_id: str, value: object) -> RuleSpec[object]:
    return RuleSpec(id=rule_id, condition={}, value=value)


def test_bundled_emit_includes_self_bootstrap() -> None:
    content = Ruleset.format_raw_value(
        "discovery_parameters:inventory_df_rules",
        [_rule("r1", {"mount": "/var"})],
        is_optional=False,
        pprint_value=True,
    )
    assert "discovery_parameters = locals().setdefault('discovery_parameters', {})" in content
    assert "discovery_parameters.setdefault('inventory_df_rules', [])" in content


def test_standalone_emit_unchanged() -> None:
    content = Ruleset.format_raw_value(
        "only_hosts",
        [_rule("r1", True)],
        is_optional=True,
        pprint_value=True,
    )
    assert "globals().setdefault('only_hosts', [])" in content
    # The standalone branch must not start touching a parent dict.
    assert "locals().setdefault" not in content


def _exec_into_empty_default(content: str, tmp_path: Path) -> Mapping[str, Any]:
    rules_mk = tmp_path / "rules.mk"
    rules_mk.write_text(content)
    return load_mk_file(rules_mk, default={}, lock=False)


def test_bundled_exec_materialises_parent_dict_in_locals(tmp_path: Path) -> None:
    content = Ruleset.format_raw_value(
        "discovery_parameters:inventory_df_rules",
        [_rule("r1", {"mount": "/var"})],
        is_optional=False,
        pprint_value=True,
    )

    environ = _exec_into_empty_default(content, tmp_path)

    assert environ["discovery_parameters"] == {
        "inventory_df_rules": [{"id": "r1", "condition": {}, "value": {"mount": "/var"}}]
    }


def test_bundled_accumulates_across_files_in_shared_context(tmp_path: Path) -> None:
    """Two folders' rules.mk for the same bundled rulespec exec into the same
    globals/locals dict (the base-config load pattern). The second file must
    not clobber the first's contribution."""
    content_a = Ruleset.format_raw_value(
        "discovery_parameters:inventory_df_rules",
        [_rule("rA", {"mount": "/a"})],
        is_optional=False,
        pprint_value=True,
    )
    content_b = Ruleset.format_raw_value(
        "discovery_parameters:inventory_df_rules",
        [_rule("rB", {"mount": "/b"})],
        is_optional=False,
        pprint_value=True,
    )

    ctx: dict[str, Any] = {}
    exec(compile(content_a, "<test_a>", "exec"), ctx, ctx)  # nosec B102
    exec(compile(content_b, "<test_b>", "exec"), ctx, ctx)  # nosec B102

    # rB prepended via `[<new>] + discovery_parameters['foo']`.
    rules = ctx["discovery_parameters"]["inventory_df_rules"]
    assert [r["id"] for r in rules] == ["rB", "rA"]


@pytest.mark.parametrize(
    "ruleset_name",
    [
        "checkgroup_parameters:filesystem",
        "static_checks:filesystem",
        "inv_parameters:inv_if",
    ],
)
def test_bundled_emit_self_bootstraps_for_every_parent(ruleset_name: str, tmp_path: Path) -> None:
    content = Ruleset.format_raw_value(
        ruleset_name,
        [_rule("r1", {})],
        is_optional=False,
        pprint_value=True,
    )
    environ = _exec_into_empty_default(content, tmp_path)
    parent, _, subkey = ruleset_name.partition(":")
    assert subkey in environ[parent]


def test_legacy_bundled_file_loads_with_preseeded_parent(tmp_path: Path) -> None:
    """Files written before the self-bootstrap format lack the
    `locals().setdefault(...)` line and rely on the loader pre-seeding the
    parent dict. That path must keep working until every rules.mk has been
    re-saved in the new format."""
    legacy = (
        "discovery_parameters.setdefault('inventory_df_rules', [])\n"
        "discovery_parameters['inventory_df_rules'] = "
        "[{'id': 'r1', 'condition': {}, 'value': {'mount': '/var'}}] "
        "+ discovery_parameters['inventory_df_rules']\n"
    )
    rules_mk = tmp_path / "rules.mk"
    rules_mk.write_text(legacy)

    environ = load_mk_file(rules_mk, default={"discovery_parameters": {}}, lock=False)

    assert environ["discovery_parameters"] == {
        "inventory_df_rules": [{"id": "r1", "condition": {}, "value": {"mount": "/var"}}]
    }
