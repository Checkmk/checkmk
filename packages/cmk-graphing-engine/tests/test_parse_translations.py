#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import MetricName, MetricTranslation
from cmk.graphing_engine._from_api import parse_translations_from_api


def test_parses_rename_scale_and_rename_and_scale() -> None:
    translation = translations_v1.Translation(
        name="example",
        check_commands=[translations_v1.PassiveCheck("foo")],
        translations={
            "renamed": translations_v1.RenameTo("new_name"),
            "scaled": translations_v1.ScaleBy(2.0),
            "both": translations_v1.RenameToAndScaleBy("other_name", 0.5),
        },
    )

    assert parse_translations_from_api([translation]) == {
        "check_mk-foo": {
            # RenameTo keeps the default scale of 1.0.
            MetricName("renamed"): MetricTranslation(name=MetricName("new_name")),
            # ScaleBy keeps the metric's own name.
            MetricName("scaled"): MetricTranslation(name=MetricName("scaled"), scale=2.0),
            MetricName("both"): MetricTranslation(name=MetricName("other_name"), scale=0.5),
        }
    }


def test_normalizes_each_kind_of_check_command() -> None:
    def _single(check_command: object) -> translations_v1.Translation:
        return translations_v1.Translation(
            name="t",
            check_commands=[check_command],  # type: ignore[list-item]
            translations={"m": translations_v1.RenameTo("m2")},
        )

    parsed = parse_translations_from_api(
        [
            _single(translations_v1.PassiveCheck("passive")),
            _single(translations_v1.ActiveCheck("active")),
            _single(translations_v1.HostCheckCommand("host")),
            # A Nagios plug-in name with a dot is normalized like the perf-data lookup key.
            _single(translations_v1.NagiosPlugin("ping.exe")),
        ]
    )

    assert set(parsed) == {
        "check_mk-passive",
        "check_mk_active-active",
        "check-mk-host",
        "check_ping_exe",
    }


def test_already_prefixed_check_command_is_left_untouched() -> None:
    translation = translations_v1.Translation(
        name="t",
        check_commands=[translations_v1.PassiveCheck("check_mk-already")],
        translations={"m": translations_v1.RenameTo("m2")},
    )
    assert set(parse_translations_from_api([translation])) == {"check_mk-already"}


def test_a_translation_applies_to_each_of_its_check_commands() -> None:
    translation = translations_v1.Translation(
        name="t",
        check_commands=[translations_v1.PassiveCheck("a"), translations_v1.PassiveCheck("b")],
        translations={"m": translations_v1.ScaleBy(3.0)},
    )
    parsed = parse_translations_from_api([translation])
    assert set(parsed) == {"check_mk-a", "check_mk-b"}
    assert parsed["check_mk-a"] == parsed["check_mk-b"]
