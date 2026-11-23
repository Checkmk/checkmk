#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.maps.gui._filter_check import check_object_filter


@pytest.mark.parametrize(
    "object_filter, object_types",
    [
        pytest.param("Filter: state != 0\n", "host", id="host-column"),
        pytest.param("Filter: host_groups >= linux\n", "service", id="service-column"),
        pytest.param("Filter: name !=~ web\n", None, id="operator-missing-in-checkmk-list"),
        pytest.param("Filter: host_name = web\n", "host", id="column-with-the-table-prefix"),
        pytest.param("Filter: service_description ~ CPU\n", "service", id="service-prefix"),
        pytest.param("Filter: name = a\nOr: 0\nAnd: 2\n", "host", id="or-of-nothing"),
    ],
)
def test_accepts_a_filter_livestatus_runs(object_filter: str, object_types: str | None) -> None:
    check_object_filter(object_filter, object_types)


@pytest.mark.parametrize(
    "object_filter, object_types",
    [
        pytest.param("Filter: description ~ CPU\n", "host", id="service-column-on-hosts"),
        pytest.param("Filter: nme = web\n", None, id="unknown-column"),
        pytest.param("Filter: name <> web\n", "host", id="unknown-operator"),
        pytest.param("Filter: name\n", "host", id="no-operator"),
        pytest.param("Filter: name = a\nOr: 2\n", "host", id="or-beyond-the-lines-before-it"),
        pytest.param("Negate:\n", "host", id="leading-negate"),
    ],
)
def test_rejects_a_filter_livestatus_refuses(object_filter: str, object_types: str | None) -> None:
    with pytest.raises(ValueError):
        check_object_filter(object_filter, object_types)
