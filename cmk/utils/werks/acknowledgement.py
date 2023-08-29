#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from functools import cache
from typing import NamedTuple

import cmk.utils.paths
import cmk.utils.store as store

from . import load
from .werk import Compatibility, Werk

ACKNOWLEDGEMENT_PATH = cmk.utils.paths.var_dir + "/acknowledged_werks.mk"


class GuiWerk(NamedTuple):
    """
    Holds original Werk and attributes only used for the GUI
    """

    werk: Werk


def is_acknowledged(werk: Werk, acknowledged_werk_ids: set[int]) -> bool:
    return werk.id in acknowledged_werk_ids or version_is_pre_127(werk.version)


def load_acknowledgements() -> set[int]:
    return set(store.load_object_from_file(ACKNOWLEDGEMENT_PATH, default=[]))


def save_acknowledgements(acknowledged_werks: list[int]) -> None:
    store.save_object_to_file(ACKNOWLEDGEMENT_PATH, acknowledged_werks)


def version_is_pre_127(version: str) -> bool:
    return version.startswith("1.2.5") or version.startswith("1.2.6")


def sort_by_date(werks: Iterable[GuiWerk]) -> list[GuiWerk]:
    return sorted(werks, key=lambda w: w.werk.date, reverse=True)


def unacknowledged_incompatible_werks() -> list[GuiWerk]:
    acknowledged_werk_ids = load_acknowledgements()
    return sort_by_date(
        werk
        for werk in load_werk_entries()
        if werk.werk.compatible == Compatibility.NOT_COMPATIBLE
        and not is_acknowledged(werk.werk, acknowledged_werk_ids)
    )


@cache
def load_werk_entries() -> Sequence[GuiWerk]:
    werks_raw = load()
    werks = []
    for werk in werks_raw.values():
        werks.append(
            GuiWerk(
                werk=werk,
            )
        )
    return werks
