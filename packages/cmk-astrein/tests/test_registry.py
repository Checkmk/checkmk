#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

import pytest

from cmk.astrein.registry import ALL_CHECKERS, all_summaries

_KEBAB_CASE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
_FORBIDDEN_WORDS = {"cmk", "check", "checker"}


def test_checker_ids_are_unique() -> None:
    ids = [checker.checker_id for checker in ALL_CHECKERS]
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize("reported_id", sorted(all_summaries()))
def test_reported_id_follows_format(reported_id: str) -> None:
    assert _KEBAB_CASE.fullmatch(reported_id)
    assert _FORBIDDEN_WORDS.isdisjoint(reported_id.split("-"))


def test_every_reported_id_has_a_nonempty_summary() -> None:
    assert all(all_summaries().values())
