#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.astrein.checkers import ALL_CHECKERS, all_summaries


def test_checker_ids_are_unique() -> None:
    ids = [checker.checker_id for checker in ALL_CHECKERS]
    assert len(set(ids)) == len(ids)


def test_every_reported_id_has_a_nonempty_summary() -> None:
    assert all(all_summaries().values())
