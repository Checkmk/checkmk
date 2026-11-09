#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.bazel.rulesets.bazel_cache import rule_spec_bazel_cache


def _migrate(value: object) -> Mapping[str, object]:
    migrate = rule_spec_bazel_cache.parameter_form().migrate
    assert migrate is not None, "rule_spec_bazel_cache has no migrate wired"
    return migrate(value)


@pytest.mark.parametrize(
    "verify",
    [
        pytest.param(True, id="verification enabled"),
        pytest.param(False, id="verification disabled"),
    ],
)
def test_migration_keeps_the_certificate_verification_setting(verify: bool) -> None:
    old_rule = {"protocol": "https", "no_cert_check": verify}

    migrated = _migrate(old_rule)

    assert migrated == {"protocol": "https", "verify_cert": verify}


def test_migration_leaves_a_migrated_rule_unchanged() -> None:
    rule = {"protocol": "https", "verify_cert": True}

    assert _migrate(rule) == rule
