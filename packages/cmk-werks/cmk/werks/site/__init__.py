#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Loading of werks from their on-disk site layout."""

from collections.abc import Iterable, Sequence
from functools import cache
from pathlib import Path

import cmk.utils.paths
from cmk.werks.tool.models import WerkV3
from cmk.werks.tool.utils import (
    load_precompiled_werks_file,
)

from .acknowledgement import load_acknowledgements, UNACKNOWLEDGED_WERKS_JSON

COMPILED_WERKS_DIR = cmk.utils.paths.share_dir / "werks"


def load(
    *,
    base_dir: Path | None = None,
    unacknowledged_werks_json: Path | None = None,
    acknowledged_werks_mk: Path | None = None,
) -> dict[int, WerkV3]:
    if base_dir is None:
        base_dir = COMPILED_WERKS_DIR
    if unacknowledged_werks_json is None:
        unacknowledged_werks_json = UNACKNOWLEDGED_WERKS_JSON

    werks: dict[int, WerkV3] = {}

    unacknowledged_werks = {}
    if unacknowledged_werks_json.exists():
        # load unacknowledged werks that are part of the configuration
        # and still not acknowledged by the user
        unacknowledged_werks = load_precompiled_werks_file(unacknowledged_werks_json)
        acknowledged_werks = load_acknowledgements(acknowledged_werks_mk=acknowledged_werks_mk)
        unacknowledged_werks = {
            werk_id: werk
            for werk_id, werk in unacknowledged_werks.items()
            if werk_id not in acknowledged_werks
        }
        werks.update(unacknowledged_werks)

    # load werks shipped with the version, they have to loaded after the unacknowledged werks,
    # as they could contain more recent content
    for file_name in [(base_dir / "werks"), *base_dir.glob("werks-*")]:
        werks.update(load_precompiled_werks_file(file_name))

    for werk_id, werk in unacknowledged_werks.items():
        # if the werk is coming from unacknowledged_werks, then we want to present it with the first
        # version we saw it.
        werks[werk_id].version = werk.version

    return werks


@cache
def load_werk_entries() -> Sequence[WerkV3]:
    # we have a small caching inconsistency here:
    # load() will also load unacknowledged incompatible werks of previous versions
    # when those werks are acknowledged, they will be visible until checkmk is restarted and this
    # cache vanishes. completely removing a werk after it was acknowledged is also not 100%
    # expected, so this caching issue might actually be a feature.
    werks_raw = load()
    return list(werks_raw.values())


def find_werk(werks: Iterable[WerkV3], werk_id: int) -> WerkV3 | None:
    return next((werk for werk in werks if werk.id == werk_id), None)
