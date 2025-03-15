#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc import store

import cmk.utils.paths

from cmk.werks.models import Werk
from cmk.werks.utils import write_precompiled_werks

ACKNOWLEDGEMENT_PATH = cmk.utils.paths.var_dir + "/acknowledged_werks.mk"
UNACKNOWLEDGED_WERKS_JSON = Path(cmk.utils.paths.var_dir, "unacknowledged_werks.json")


def is_acknowledged(werk: Werk, acknowledged_werk_ids: set[int]) -> bool:
    return werk.id in acknowledged_werk_ids or version_is_pre_127(werk.version)


def load_acknowledgements() -> set[int]:
    return set(store.load_object_from_file(ACKNOWLEDGEMENT_PATH, default=[]))


def save_acknowledgements(acknowledged_werks: list[int]) -> None:
    store.save_object_to_file(ACKNOWLEDGEMENT_PATH, acknowledged_werks)


def version_is_pre_127(version: str) -> bool:
    return version.startswith("1.2.5") or version.startswith("1.2.6")


def write_unacknowledged_werks(werks: dict[int, Werk]) -> None:
    write_precompiled_werks(UNACKNOWLEDGED_WERKS_JSON, werks)
