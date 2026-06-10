#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.quick_setup.config_setups.aws.form_specs import (
    _get_edition_specific_choices,
    _ServiceChoices,
    register_extended_aws_service_choices,
)

_EXTENDED_REGIONAL = {"aws_lambda", "sns", "ecs", "elasticache"}


def test_migrate_drops_extended_choices_on_downgrade() -> None:
    # Pro (aws_extended off): only the base choices are valid. A config saved on Ultimate
    # that selected extended services must survive edit/activate by silently dropping them.
    base_regional = {c.name for c in _ServiceChoices().regional_services}
    migrate = _get_edition_specific_choices(base_regional)

    # Fake stored config: base choices (still valid) + extended choices (invalid once the flag is off).
    stored = ["ec2", "s3", *_EXTENDED_REGIONAL]

    # Migrate should drop the extended choices, keeping only the valid ones.
    result = migrate(stored)

    assert set(result) <= base_regional
    assert {"ec2", "s3"} <= set(result)
    assert not (set(result) & _EXTENDED_REGIONAL)


def test_migrate_keeps_choices_when_valid() -> None:
    # Ultimate (aws_extended on): extended choices are valid and preserved as-is.
    choices = _ServiceChoices()

    # Register extended choices, as they would be when the flag is on.
    register_extended_aws_service_choices(choices)

    # Valid choices = the full regional set: base (from _ServiceChoices) + extended (added by the helper).
    valid = {c.name for c in choices.regional_services}

    # The migrate is a no-op when every stored choice is still valid.
    migrate = _get_edition_specific_choices(valid)

    # Fake stored config: a base choice + extended choices, all valid in this Ultimate case.
    stored = ["ec2", *_EXTENDED_REGIONAL]
    assert set(migrate(stored)) == set(stored)


def test_migrate_rejects_non_iterable() -> None:
    migrate = _get_edition_specific_choices({"ec2"})
    with pytest.raises(TypeError):
        migrate(42)
