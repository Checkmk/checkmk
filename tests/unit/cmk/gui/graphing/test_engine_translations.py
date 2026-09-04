#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing.v1 import translations
from cmk.graphing_engine import MetricName
from cmk.gui.graphing._engine_perfdata import RawPerformanceData, RawPerformanceValue
from cmk.gui.graphing._engine_translations import (
    map_metric_names,
    reverse_translated_names,
    rrd_originals,
    RRDOriginal,
    translate_metric_names,
    translate_performance_data,
)

# The check the translations below are registered for, as a passive check's performance data spells
# it and as the plug-in names it.
_CHECK_COMMAND = "check_mk-foo"
_CHECK_PLUGIN = "foo"

type _Specs = Mapping[
    str, translations.RenameTo | translations.ScaleBy | translations.RenameToAndScaleBy
]


def _registered(specs: _Specs) -> Sequence[translations.Translation]:
    return [
        translations.Translation(
            name="t",
            check_commands=[translations.PassiveCheck(_CHECK_PLUGIN)],
            translations=specs,
        )
    ]


def _raw(values: Mapping[str, RawPerformanceValue]) -> RawPerformanceData:
    return RawPerformanceData(
        check_command=_CHECK_COMMAND,
        values={MetricName(name): value for name, value in values.items()},
    )


def _original(name: str, scale: float) -> RRDOriginal:
    return RRDOriginal(metric_name=MetricName(name), scale=scale)


def test_map_metric_names_pairs_raw_names_with_their_canonical_names() -> None:
    # A set of canonical names cannot say which raw column produced which name; the mapping can. A
    # raw name no translation renames is its own canonical name, so no raw name is dropped.
    assert dict(
        map_metric_names(
            _CHECK_COMMAND,
            [MetricName("old"), MetricName("untouched")],
            _registered({"old": translations.RenameTo("new")}),
        )
    ) == {MetricName("old"): MetricName("new"), MetricName("untouched"): MetricName("untouched")}


def test_two_raw_names_sharing_a_canonical_name_keep_their_own_entries() -> None:
    # The case the frozenset cannot express at all: it reports one name where two columns exist, so
    # a caller reading it back has no way to tell which of them it may ask an RRD for.
    assert dict(
        map_metric_names(
            _CHECK_COMMAND,
            [MetricName("if_in_octets"), MetricName("if_out_octets")],
            _registered({"~if_.*_octets": translations.RenameTo("if_octets")}),
        )
    ) == {
        MetricName("if_in_octets"): MetricName("if_octets"),
        MetricName("if_out_octets"): MetricName("if_octets"),
    }


def test_a_scaling_translation_leaves_the_name_alone() -> None:
    # A translation that only scales is still a translation, and a caller that resolves a name
    # through the mapping has to get the raw name back rather than nothing.
    assert dict(
        map_metric_names(
            _CHECK_COMMAND,
            [MetricName("mem")],
            _registered({"mem": translations.ScaleBy(1024)}),
        )
    ) == {MetricName("mem"): MetricName("mem")}


def test_metric_names_are_reported_under_their_canonical_name() -> None:
    assert translate_metric_names(
        _CHECK_COMMAND,
        [MetricName("old"), MetricName("untouched")],
        _registered({"old": translations.RenameTo("new")}),
    ) == {MetricName("new"), MetricName("untouched")}


def test_a_predictive_metric_keeps_its_prefix_while_its_base_is_renamed() -> None:
    # The prediction of a renamed metric is stored under the prefixed old name, so the prefix has to
    # survive the rename rather than being translated as part of the name.
    assert translate_metric_names(
        _CHECK_COMMAND,
        [MetricName("predict_old"), MetricName("predict_lower_old")],
        _registered({"old": translations.RenameTo("new")}),
    ) == {MetricName("predict_new"), MetricName("predict_lower_new")}


def test_a_regex_translation_matches_by_pattern() -> None:
    assert translate_metric_names(
        _CHECK_COMMAND,
        [MetricName("if_out_octets")],
        _registered({"~if_.*_octets": translations.RenameTo("if_octets")}),
    ) == {MetricName("if_octets")}


def test_an_unregistered_check_command_translates_nothing() -> None:
    assert translate_metric_names(
        "check_mk-other",
        [MetricName("old")],
        _registered({"old": translations.RenameTo("new")}),
    ) == {MetricName("old")}


def test_a_scaling_translation_scales_the_value_and_every_threshold() -> None:
    [(name, data)] = translate_performance_data(
        _CHECK_COMMAND,
        {
            MetricName("x"): RawPerformanceValue(
                value=5.0,
                warning=7.0,
                critical=9.0,
                lower_warning=3.0,
                lower_critical=1.0,
                minimum=0.0,
                maximum=10.0,
            )
        },
        _registered({"x": translations.ScaleBy(1024)}),
    ).items()
    assert name == MetricName("x")
    assert (data.value, data.warning, data.critical) == (5120.0, 7168.0, 9216.0)
    assert (data.lower_warning, data.lower_critical) == (3072.0, 1024.0)
    assert (data.minimum, data.maximum) == (0.0, 10240.0)


def test_an_absent_threshold_stays_absent_when_scaled() -> None:
    [(_name, data)] = translate_performance_data(
        _CHECK_COMMAND,
        {MetricName("x"): RawPerformanceValue(value=5.0)},
        _registered({"x": translations.ScaleBy(1024)}),
    ).items()
    assert data.warning is None
    assert data.maximum is None


def test_a_metric_is_drawn_from_the_column_its_data_was_translated_from() -> None:
    # The canonical name has no RRD of its own here: the series comes from the column the performance
    # data carried, and it carries the factor the value was scaled by.
    assert rrd_originals(
        MetricName("new"),
        _raw({"old": RawPerformanceValue(value=5.0)}),
        _registered({"old": translations.RenameToAndScaleBy("new", 1000)}),
    ) == [_original("old", 1000.0)]


def test_two_columns_translated_onto_one_metric_are_both_drawn() -> None:
    assert rrd_originals(
        MetricName("m"),
        _raw({"a": RawPerformanceValue(value=1.0), "b": RawPerformanceValue(value=2.0)}),
        _registered({"a": translations.RenameTo("m"), "b": translations.RenameTo("m")}),
    ) == [_original("a", 1.0), _original("b", 1.0)]


def test_a_deprecated_column_absent_from_the_performance_data_is_still_drawn() -> None:
    # The old column is gone from the performance data but its RRD may still be around, so it is read
    # alongside the current one - scaled by the translation that renamed it.
    assert rrd_originals(
        MetricName("new"),
        _raw({"new": RawPerformanceValue(value=5.0)}),
        _registered({"old": translations.RenameToAndScaleBy("new", 1000)}),
    ) == [_original("new", 1.0), _original("old", 1000.0)]


def test_a_metric_without_performance_data_falls_back_to_its_own_column_unscaled() -> None:
    assert rrd_originals(
        MetricName("y"),
        _raw({"x": RawPerformanceValue(value=5.0)}),
        _registered({"x": translations.ScaleBy(1024)}),
    ) == [_original("y", 1.0)]


def test_reverse_translated_names_always_contains_the_metric_itself() -> None:
    assert reverse_translated_names(MetricName("new"), []) == {MetricName("new")}


def test_reverse_translated_names_collects_every_name_renamed_to_it() -> None:
    assert reverse_translated_names(
        MetricName("new"),
        [
            *_registered({"old": translations.RenameTo("new")}),
            *_registered({"ancient": translations.RenameToAndScaleBy("new", 2.0)}),
        ],
    ) == {MetricName("new"), MetricName("old"), MetricName("ancient")}


def test_reverse_translated_names_skips_a_regex_translation() -> None:
    # "~.*rta" maps many raw names onto one canonical name, so it cannot be reversed.
    assert reverse_translated_names(
        MetricName("rta"), _registered({"~.*rta": translations.RenameTo("rta")})
    ) == {MetricName("rta")}


def test_reverse_translated_names_ignores_a_translation_to_another_metric() -> None:
    assert reverse_translated_names(
        MetricName("new"), _registered({"old": translations.RenameTo("other")})
    ) == {MetricName("new")}
