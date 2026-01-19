#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import cmk.utils.paths
from cmk.ccc import store
from cmk.werks.models import WerkV2, WerkV3
from cmk.werks.utils import write_precompiled_werks

ACKNOWLEDGEMENT_PATH = cmk.utils.paths.var_dir / "acknowledged_werks.mk"
UNACKNOWLEDGED_WERKS_JSON = cmk.utils.paths.var_dir / "unacknowledged_werks.json"


def is_acknowledged(werk: WerkV2 | WerkV3, acknowledged_werk_ids: set[int]) -> bool:
    return werk.id in acknowledged_werk_ids


def load_acknowledgements(
    *,
    acknowledged_werks_mk: Path | None = None,
) -> set[int]:
    if acknowledged_werks_mk is None:
        acknowledged_werks_mk = ACKNOWLEDGEMENT_PATH
    return set(store.load_object_from_file(acknowledged_werks_mk, default=[]))


def save_acknowledgements(
    acknowledged_werks: list[int],
    *,
    acknowledged_werks_mk: Path = ACKNOWLEDGEMENT_PATH,
) -> None:
    store.save_object_to_file(acknowledged_werks_mk, acknowledged_werks)


def write_unacknowledged_werks(
    werks: dict[int, WerkV2 | WerkV3],
    *,
    unacknowledged_werks_json: Path | None = None,
) -> None:
    if unacknowledged_werks_json is None:
        unacknowledged_werks_json = UNACKNOWLEDGED_WERKS_JSON
    write_precompiled_werks(unacknowledged_werks_json, werks)
