#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.diagnostics.internal import (
    DiagnosticsPlugin,
    entry_point_prefixes,
    Help,
    Sensitivity,
    Topic,
)


def test_entry_point_prefixes() -> None:
    assert entry_point_prefixes() == {DiagnosticsPlugin: "diagnostics_plugin_"}


def test_plugin_defaults() -> None:
    plugin = DiagnosticsPlugin(
        name="name",
        topic=Topic("topic"),
        description=Help("Collects something."),
        sensitivity=Sensitivity.LOW,
        handler=lambda *_a: (),
    )
    assert not plugin.always


def test_sensitivity_is_ordered() -> None:
    assert Sensitivity.LOW < Sensitivity.MEDIUM < Sensitivity.HIGH
    assert Sensitivity.HIGH >= Sensitivity.MEDIUM
    assert max(Sensitivity.MEDIUM, Sensitivity.LOW) is Sensitivity.MEDIUM


def test_localizables_localize() -> None:
    def _translate(string: str) -> str:
        return {"Test topic": "Testthema"}.get(string, string)

    assert Topic("Test topic").localize(_translate) == "Testthema"
    assert (Help("A. ") + Help("B.")).localize(str) == "A. B."
