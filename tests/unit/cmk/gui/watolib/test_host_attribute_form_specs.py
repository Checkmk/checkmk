#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Collection
from typing import NamedTuple

import pytest

from cmk.gui.config import active_config
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.watolib.host_attributes import (
    ABCHostAttributeValueSpec,
    all_host_attributes,
)
from cmk.rulesets.v1.form_specs import FormSpec


def _all_value_spec_attributes() -> dict[str, ABCHostAttributeValueSpec]:
    return {
        name: attr
        for name, attr in all_host_attributes(
            active_config.wato_host_attrs,
            active_config.tags.get_tag_groups_by_topic(),
        ).items()
        if isinstance(attr, ABCHostAttributeValueSpec)
    }


_FORM_SPEC_DEFAULT_MISMATCHES = {
    "snmp_community",
    "management_snmp_community",
}


class RoundTrip(NamedTuple):
    ok: bool
    detail: str


def _validate_value_spec_default_value(attr: ABCHostAttributeValueSpec) -> RoundTrip:
    value_spec = attr.valuespec()
    default = attr.default_value()
    try:
        transformed = value_spec.transform_value(default)
    except Exception as exc:
        return RoundTrip(False, f"round-trip raised: {exc!r}")
    if transformed != default:
        return RoundTrip(
            False, f"transform_value changed the value: {transformed!r} != {default!r}"
        )
    return RoundTrip(True, "")


def _validate_form_spec_default_value(form_spec: FormSpec[object], default: object) -> RoundTrip:
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=False, mask_values=False))
    raw = RawDiskData(default)
    try:
        on_disk = visitor.to_disk(raw)
    except Exception as exc:
        return RoundTrip(False, f"to_disk raised: {exc!r}")
    if on_disk != default:
        return RoundTrip(False, f"to_disk changed the value: {on_disk!r} != {default!r}")
    return RoundTrip(True, "")


def _assert_round_trips(
    kind: str, results: dict[str, RoundTrip], skip: Collection[str] = ()
) -> None:
    failures: list[str] = []
    for name, result in sorted(results.items()):
        if not result.ok and name not in skip:
            failures.append(f"{name}: {result.detail}")

    assert not failures, f"{kind} failed to round-trip the default value of:\n" + "\n".join(
        failures
    )


@pytest.mark.usefixtures("load_config")
def test_host_attribute_round_trip_default_value() -> None:
    value_spec_results: dict[str, RoundTrip] = {}
    form_spec_results: dict[str, RoundTrip] = {}
    for name, attr in _all_value_spec_attributes().items():
        value_spec_results[name] = _validate_value_spec_default_value(attr)

        form_spec_results[name] = _validate_form_spec_default_value(
            attr.form_spec(), attr.default_value()
        )

    _assert_round_trips("ValueSpec", value_spec_results)
    _assert_round_trips("FormSpec", form_spec_results, skip=_FORM_SPEC_DEFAULT_MISMATCHES)


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize("name", sorted(_FORM_SPEC_DEFAULT_MISMATCHES))
def test_form_spec_default_value_is_unrepresentable_none(name: str) -> None:
    """These attributes default to ``None`` in the ValueSpec, but their native FormSpec has no
    representation for ``None`` yet, so serializing the default fails."""
    attr = _all_value_spec_attributes()[name]
    assert attr.default_value() is None

    result = _validate_form_spec_default_value(attr.form_spec(), None)
    assert result.ok is False
    assert "Unable to serialize invalid value" in result.detail
