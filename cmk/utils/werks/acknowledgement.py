#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from functools import cache

from cmk.ccc import store

import cmk.utils.paths

from cmk.werks.models import Compatibility, Werk

from . import load

ACKNOWLEDGEMENT_PATH = cmk.utils.paths.var_dir + "/acknowledged_werks.mk"


def is_acknowledged(werk: Werk, acknowledged_werk_ids: set[int]) -> bool:
    return werk.id in acknowledged_werk_ids or version_is_pre_127(werk.version)


def load_acknowledgements() -> set[int]:
    return set(store.load_object_from_file(ACKNOWLEDGEMENT_PATH, default=[]))


def save_acknowledgements(acknowledged_werks: list[int]) -> None:
    store.save_object_to_file(ACKNOWLEDGEMENT_PATH, acknowledged_werks)


def version_is_pre_127(version: str) -> bool:
    return version.startswith("1.2.5") or version.startswith("1.2.6")


def sort_by_date(werks: Iterable[Werk]) -> list[Werk]:
    return sorted(werks, key=lambda werk: werk.date, reverse=True)


def unacknowledged_incompatible_werks() -> list[Werk]:
    acknowledged_werk_ids = load_acknowledgements()
    return sort_by_date(
        werk
        for werk in load_werk_entries()
        if werk.compatible == Compatibility.NOT_COMPATIBLE
        and not is_acknowledged(werk, acknowledged_werk_ids)
    )


@cache
def load_werk_entries() -> Sequence[Werk]:
    werks_raw = load()
    return list(werks_raw.values())
