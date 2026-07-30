#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from tests.testlib.site import Site

LOGGER = logging.getLogger(__name__)

LEGACY_RULESET = "agent_config:mk_oracle"
UNIFIED_RULESET = "agent_config:mk_oracle_unified"


@pytest.mark.skip_if_edition("community", "cloud")
def test_cmk_migrate_oracle_rulesets(site: Site) -> None:
    # E2E sanity check only — field-mapping coverage is in test_mk_oracle_migration(_ruleset).py.
    legacy_rule_id = site.openapi.rules.create(
        ruleset_name=LEGACY_RULESET,
        value={"activated": True, "login": {"auth": "wallet"}, "sids": ("only", ["ORCL"])},
        folder="/",
    )
    site.activate_changes_and_wait_for_core_reload()

    try:
        # First run: migrates the seeded legacy rule.
        p = site.run(["cmk-migrate-oracle-rulesets", "--apply"])
        LOGGER.info("STDOUT: %s", p.stdout)
        LOGGER.info("STDERR: %s", p.stderr)
        p.check_returncode()

        migrated_ids = site.openapi.rules.get_all_names(UNIFIED_RULESET)
        assert len(migrated_ids) == 1

        # Second run: must not duplicate the already-migrated rule.
        p = site.run(["cmk-migrate-oracle-rulesets", "--apply"])
        LOGGER.info("STDOUT: %s", p.stdout)
        LOGGER.info("STDERR: %s", p.stderr)
        p.check_returncode()

        assert site.openapi.rules.get_all_names(UNIFIED_RULESET) == migrated_ids
    finally:
        for rule_id in site.openapi.rules.get_all_names(UNIFIED_RULESET):
            site.openapi.rules.delete(rule_id)
        site.openapi.rules.delete(legacy_rule_id)
        site.activate_changes_and_wait_for_core_reload()


@pytest.mark.skip_if_edition("community", "cloud")
def test_cmk_migrate_oracle_rulesets_disables_legacy_rule(site: Site) -> None:
    legacy_rule_id = site.openapi.rules.create(
        ruleset_name=LEGACY_RULESET,
        value={"activated": True, "login": {"auth": "wallet"}, "sids": ("only", ["ORCL"])},
        folder="/",
    )
    site.activate_changes_and_wait_for_core_reload()

    try:
        p = site.run(["cmk-migrate-oracle-rulesets", "--apply", "--enable-migrated-rules"])
        LOGGER.info("STDOUT: %s", p.stdout)
        LOGGER.info("STDERR: %s", p.stderr)
        p.check_returncode()

        # Both plug-ins cannot be deployed to the same host, so enabling the migrated rule must
        # disable the legacy rule it replaces — and that has to survive the write to disk.
        (migrated_rule,) = site.openapi.rules.get_all(UNIFIED_RULESET)
        assert migrated_rule["extensions"]["properties"].get("disabled", False) is False

        (legacy_rule,) = site.openapi.rules.get_all(LEGACY_RULESET)
        assert legacy_rule["extensions"]["properties"]["disabled"] is True
    finally:
        for rule_id in site.openapi.rules.get_all_names(UNIFIED_RULESET):
            site.openapi.rules.delete(rule_id)
        site.openapi.rules.delete(legacy_rule_id)
        site.activate_changes_and_wait_for_core_reload()


@pytest.mark.skip_if_edition("community", "cloud")
def test_cmk_migrate_oracle_rulesets_keeps_disabled_legacy_rule_disabled(site: Site) -> None:
    legacy_rule_id = site.openapi.rules.create(
        ruleset_name=LEGACY_RULESET,
        value={"activated": True, "login": {"auth": "wallet"}, "sids": ("only", ["ORCL"])},
        folder="/",
        properties={"disabled": True},
    )
    site.activate_changes_and_wait_for_core_reload()

    try:
        p = site.run(["cmk-migrate-oracle-rulesets", "--apply", "--enable-migrated-rules"])
        LOGGER.info("STDOUT: %s", p.stdout)
        LOGGER.info("STDERR: %s", p.stderr)
        p.check_returncode()

        # The flag enables the rules that were active. A legacy rule the user had switched off must
        # not be activated by migrating it.
        (migrated_rule,) = site.openapi.rules.get_all(UNIFIED_RULESET)
        assert migrated_rule["extensions"]["properties"]["disabled"] is True
    finally:
        for rule_id in site.openapi.rules.get_all_names(UNIFIED_RULESET):
            site.openapi.rules.delete(rule_id)
        site.openapi.rules.delete(legacy_rule_id)
        site.activate_changes_and_wait_for_core_reload()
