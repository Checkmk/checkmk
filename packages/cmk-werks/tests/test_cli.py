#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from itertools import chain

import pytest

from cmk.werks.cli import _reserve_werk_ids, WerkId


def tw(data: Iterable[int]) -> list[WerkId]:
    return [WerkId(d) for d in data]


@pytest.mark.parametrize(
    ("first_free", "count_requested", "expected_new_first_free", "expected_ids_reserved"),
    [
        pytest.param(
            10,
            5,
            15,
            tw(range(10, 15)),
            id="request 5 ids, starting from 10",
        ),
        pytest.param(
            12,
            2,
            14,
            tw(range(12, 14)),
            id="request 2 ids, from the middle",
        ),
        pytest.param(
            32,
            2,
            34,
            tw(range(32, 34)),
            id="request 2 ids, from middle of second range",
        ),
        pytest.param(
            10,
            11,
            31,
            tw(chain(range(10, 20), [30])),
            id="request whole first range",
        ),
        pytest.param(
            10,
            25,
            55,
            tw(chain(range(10, 20), range(30, 40), range(50, 55))),
            id="ids from three ranges",
        ),
    ],
)
def test_reserve_werk_id(
    first_free, count_requested, expected_new_first_free, expected_ids_reserved
):
    new_first_free, ids_reserved = _reserve_werk_ids(
        [(10, 20), (30, 40), (50, 60)], first_free, count_requested
    )

    assert len(ids_reserved) == count_requested
    assert expected_new_first_free == new_first_free
    assert expected_ids_reserved == ids_reserved


def test_reserve_werk_id_fails():
    with pytest.raises(RuntimeError, match="Configuration error"):
        # first_free does not match the range we should actually be in
        _reserve_werk_ids([(10, 20), (30, 40), (50, 60)], 25, 5)

    with pytest.raises(RuntimeError, match="Not enough ids available"):
        # too many ids requested
        _reserve_werk_ids([(10, 20), (30, 40), (50, 60)], 15, 200)
