#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import AbstractContextManager as ContextManager
from contextlib import nullcontext
from typing import Literal

import pytest

from cmk.utils.labels import LabelGroups

from cmk.gui.exceptions import MKUserError
from cmk.gui.query_filters import AllLabelGroupsQuery
from cmk.gui.type_defs import FilterHTTPVariables


@pytest.mark.parametrize(
    "object_type, value, parsed_value, expectation, error_msg",
    [
        pytest.param(
            "host",
            {
                "host_labels_count": "2",
                # Group 1
                "host_labels_1_vs_count": "2",
                "host_labels_1_bool": "and",
                "host_labels_1_vs_1_bool": "and",
                "host_labels_1_vs_1_vs": "label:abc",
                "host_labels_1_vs_2_bool": "or",
                "host_labels_1_vs_2_vs": "label:xyz",
                # Group 2
                "host_labels_2_vs_count": "1",
                "host_labels_2_bool": "not",
                "host_labels_2_vs_1_bool": "and",
                "host_labels_2_vs_1_vs": "label:mno",
            },
            [
                ("and", [("and", "label:abc"), ("or", "label:xyz")]),
                ("not", [("and", "label:mno")]),
            ],
            nullcontext(),
            None,
        ),
        pytest.param(
            "service",
            {
                "service_labels_count": "2",
                # Group 1
                "service_labels_1_vs_count": "2",
                "service_labels_1_bool": "and",
                "service_labels_1_vs_1_bool": "and",
                "service_labels_1_vs_1_vs": "label:abc",
                "service_labels_1_vs_2_bool": "or",
                "service_labels_1_vs_2_vs": "label:xyz",
                # Group 2
                "service_labels_2_vs_count": "1",
                "service_labels_2_bool": "not",
                "service_labels_2_vs_1_bool": "and",
                "service_labels_2_vs_1_vs": "label:mno",
            },
            [
                ("and", [("and", "label:abc"), ("or", "label:xyz")]),
                ("not", [("and", "label:mno")]),
            ],
            nullcontext(),
            None,
        ),
        pytest.param(
            "host",
            {
                "host_labels_count": "not an integer",
            },
            [],
            pytest.raises(MKUserError),
            'The value "not an integer" of HTTP variable "host_labels_count" is not an integer.',
        ),
        pytest.param(
            "service",
            {
                "service_labels_count": "1",
                # Group 1
                "service_labels_1_vs_count": "2",
                "service_labels_1_bool": "annnd",
            },
            [],
            pytest.raises(MKUserError),
            'The value "annnd" of HTTP variable "service_labels_1_bool" is not a valid operator ({"and", "or", "not"}).',
        ),
    ],
)
def test_label_value_parsing(
    object_type: Literal["host", "service"],
    value: FilterHTTPVariables,
    parsed_value: LabelGroups,
    expectation: ContextManager,
    error_msg: str | None,
) -> None:
    inst: AllLabelGroupsQuery = AllLabelGroupsQuery(object_type=object_type)
    with expectation as e:
        assert parsed_value == inst.parse_value(value)
    assert error_msg is None or error_msg in str(e)
