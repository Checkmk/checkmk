#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Which groups of a span survive the active filters (CMK-35309).

Livestatus selects the spans, but a matching span also carries the groups the user did
not select. Those become extra groups of the availability table unless the filters get
to say which of them were asked for.
"""

from typing import cast, Literal

from cmk.gui.availability.computation import filter_groups_of_entries
from cmk.gui.availability.type_defs import AVSpan
from cmk.gui.type_defs import VisualContext
from cmk.gui.visuals import get_filter

_GROUP_FILTERS = ("servicegroups", "optservicegroup", "hostgroups", "opthostgroup")


def _span(groups: list[str]) -> AVSpan:
    return cast(AVSpan, {"service_groups": list(groups), "host_groups": list(groups)})


def _filter(
    context: VisualContext,
    grouping: Literal["host_groups", "service_groups"],
    spans: list[AVSpan],
) -> None:
    filter_groups_of_entries(
        context, [get_filter(ident) for ident in _GROUP_FILTERS], grouping, spans
    )


def _several_service_groups(selection: str, negate: str = "") -> VisualContext:
    return {"servicegroups": {"servicegroups": selection, "neg_servicegroups": negate}}


def _service_is_in_group(group: str, negate: str = "") -> VisualContext:
    return {"optservicegroup": {"optservice_group": group, "neg_optservice_group": negate}}


def _several_host_groups(selection: str, negate: str = "") -> VisualContext:
    return {"hostgroups": {"hostgroups": selection, "neg_hostgroups": negate}}


def _host_is_in_group(group: str, negate: str = "") -> VisualContext:
    return {"opthostgroup": {"opthost_group": group, "neg_opthost_group": negate}}


def test_the_groups_beside_the_selected_one_are_dropped() -> None:
    spans = [_span(["mem", "cpu", "disk"])]

    _filter(_several_service_groups("cpu"), "service_groups", spans)

    assert spans[0]["service_groups"] == ["cpu"]


def test_every_selected_group_is_kept() -> None:
    spans = [_span(["mem", "cpu", "disk"])]

    _filter(_several_service_groups("cpu|disk"), "service_groups", spans)

    assert spans[0]["service_groups"] == ["cpu", "disk"]


def test_a_negated_group_is_dropped() -> None:
    spans = [_span(["mem", "cpu", "disk"])]

    _filter(_several_service_groups("cpu", negate="on"), "service_groups", spans)

    assert spans[0]["service_groups"] == ["mem", "disk"]


def test_the_single_group_filter_drops_the_others() -> None:
    spans = [_span(["mem", "cpu", "disk"])]

    _filter(_service_is_in_group("cpu"), "service_groups", spans)

    assert spans[0]["service_groups"] == ["cpu"]


def test_a_negated_single_group_does_not_discard_the_selection() -> None:
    # CMK-35309: the negated filter used to abort the whole restriction, so the groups
    # beside the selected ones stayed and showed up as own availability tables
    spans = [_span(["mem", "cpu", "disk"])]

    _filter(
        {**_several_service_groups("cpu|disk"), **_service_is_in_group("disk", negate="on")},
        "service_groups",
        spans,
    )

    assert spans[0]["service_groups"] == ["cpu"]


def test_two_negated_filters_drop_both_of_their_groups() -> None:
    spans = [_span(["mem", "cpu", "disk"])]

    _filter(
        {
            **_several_service_groups("cpu", negate="on"),
            **_service_is_in_group("disk", negate="on"),
        },
        "service_groups",
        spans,
    )

    assert spans[0]["service_groups"] == ["mem"]


def test_a_span_of_no_selected_group_ends_up_without_groups() -> None:
    spans = [_span(["mem"])]

    _filter(_several_service_groups("cpu"), "service_groups", spans)

    assert spans[0]["service_groups"] == []


def test_a_selected_group_no_span_is_in_is_not_invented() -> None:
    spans = [_span(["cpu"])]

    _filter(_several_service_groups("cpu|disk"), "service_groups", spans)

    assert spans[0]["service_groups"] == ["cpu"]


def test_every_span_is_narrowed_on_its_own() -> None:
    spans = [_span(["cpu", "mem"]), _span(["disk"]), _span(["cpu", "disk"])]

    _filter(_several_service_groups("cpu"), "service_groups", spans)

    assert [span["service_groups"] for span in spans] == [["cpu"], [], ["cpu"]]


def test_without_any_group_filter_the_groups_stay_as_they_are() -> None:
    spans = [_span(["mem", "cpu"])]

    _filter({}, "service_groups", spans)

    assert spans[0]["service_groups"] == ["mem", "cpu"]


def test_an_empty_group_filter_keeps_every_group() -> None:
    # The builtin service views carry an empty "Host is in group" in their context, which
    # used to wipe the host groups of every span
    spans = [_span(["linux", "windows"])]

    _filter(_host_is_in_group(""), "host_groups", spans)

    assert spans[0]["host_groups"] == ["linux", "windows"]


def test_a_filter_of_another_column_keeps_every_group() -> None:
    spans = [_span(["linux", "windows"])]

    _filter(_several_service_groups("linux"), "host_groups", spans)

    assert spans[0]["host_groups"] == ["linux", "windows"]


def test_host_groups_are_narrowed_like_service_groups() -> None:
    spans = [_span(["linux", "windows"])]

    _filter(_several_host_groups("linux"), "host_groups", spans)

    assert spans[0]["host_groups"] == ["linux"]


def test_a_negated_single_host_group_does_not_discard_the_selection() -> None:
    spans = [_span(["linux", "windows", "kubernetes"])]

    _filter(
        {**_several_host_groups("linux|windows"), **_host_is_in_group("windows", negate="on")},
        "host_groups",
        spans,
    )

    assert spans[0]["host_groups"] == ["linux"]
