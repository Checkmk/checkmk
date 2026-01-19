#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from logging import Logger
from pathlib import Path

import pytest
from pydantic import TypeAdapter

import cmk.utils.werks
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.werks import load_unacknowledged_werks, UnacknowledgedWerks
from cmk.werks.models import Class, Compatibility, EditionV2, Level, WerkV2, WerkV3


def generate_werk(
    version: str, id_: int, compatible: Compatibility = Compatibility.COMPATIBLE
) -> dict[int, WerkV2 | WerkV3]:
    werk = WerkV2(
        id=id_,
        class_=Class.FIX,
        compatible=compatible,
        component="component",
        level=Level.LEVEL_1,
        date=datetime.datetime.now(),
        edition=EditionV2.CCE,
        description="description ut",
        title="title ut",
        version=version,
    )
    return {werk.id: werk}


WERKS_240 = {
    **generate_werk("2.4.0p3", 30, compatible=Compatibility.NOT_COMPATIBLE),
    **generate_werk("2.4.0p3", 35),
    **generate_werk("2.4.0p3", 40, compatible=Compatibility.NOT_COMPATIBLE),
}

WERKS_250 = {
    **generate_werk("2.5.0p2", 30, compatible=Compatibility.NOT_COMPATIBLE),
    **generate_werk("2.5.0p2", 50, compatible=Compatibility.NOT_COMPATIBLE),
    **generate_werk("2.5.0p2", 55),
    **generate_werk("2.5.0p2", 60, compatible=Compatibility.NOT_COMPATIBLE),
}
WERKS_260: dict[int, WerkV2 | WerkV3] = {}


def test_update_livecycle() -> None:
    # we start with a 2.4.0:
    unacknowledged_werks: dict[int, WerkV2 | WerkV3] = {}  # does not exist in 2.3.0
    acknowledge_werks = {11, 12}  # some very early werks have been acknowledged

    # update from 2.3.0 to 2.4.0:
    # (this means, we have to backport this action into the 2.4.0!)
    unacknowledged_werks = load_unacknowledged_werks(
        acknowledge_werks, {**WERKS_240, **unacknowledged_werks}
    )
    assert set(unacknowledged_werks.keys()) == {30, 40}

    acknowledge_werks.add(30)  # user acknowledges one werk, but not all of them

    # update from 2.4.0 to 2.5.0:
    unacknowledged_werks = load_unacknowledged_werks(
        acknowledge_werks, {**WERKS_250, **unacknowledged_werks}
    )
    assert set(unacknowledged_werks.keys()) == {40, 50, 60}


def test_version_of_werk_keeps_first_incompatible_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unacknowledged_werks_file = Path(tmp_path, "ut_unacked")
    acknowledge_werks_file = Path(tmp_path, "ut_acked")
    compiled_werks_dir = Path(tmp_path, "ut_compiled")
    compiled_werks_dir.mkdir()

    def save_werks_to_site(werks: dict[int, WerkV2 | WerkV3]) -> None:
        adapter = TypeAdapter(dict[int, WerkV2 | WerkV3])  # nosemgrep: type-adapter-detected
        (compiled_werks_dir / "werks").write_bytes(adapter.dump_json(werks, by_alias=True))

    def update_config() -> None:
        UnacknowledgedWerks(
            name="name", title="title", sort_index=2, expiry_version=ExpiryVersion.NEVER
        )(
            Logger(__name__),
            acknowledged_werks_mk=acknowledge_werks_file,
            unacknowledged_werks_json=unacknowledged_werks_file,
            compiled_werks_folder=compiled_werks_dir,
        )

    def werks_load() -> dict[int, WerkV2 | WerkV3]:
        return cmk.utils.werks.load(
            base_dir=compiled_werks_dir,
            unacknowledged_werks_json=unacknowledged_werks_file,
            acknowledged_werks_mk=acknowledge_werks_file,
        )

    # we start with a 2.4.0:
    save_werks_to_site(WERKS_240)
    cmk.utils.werks.acknowledgement.save_acknowledgements(
        [11, 40], acknowledged_werks_mk=acknowledge_werks_file
    )
    # we updated to this 2.4.0 so somewhen this update action was executed
    update_config()

    werks = werks_load()
    # we only see all werks from 2.4.0:
    assert set(werks) == {30, 35, 40}

    # let's update to 2.5.0:
    save_werks_to_site(WERKS_250)
    update_config()
    # update done :-)

    werks = werks_load()
    # we see werks from 2.5.0 and one from 2.4.0:
    assert set(werks) == {30, 50, 55, 60}
    # werk 30 is available in both: 2.5.0 and 2.4.0, but we want to see the 2.4.0 version here,
    # as this is the first time when the customer missed to acknowledge it.
    assert werks[30].version == "2.4.0p3"

    # acknowledge the werk in 2.5.0
    cmk.utils.werks.acknowledgement.save_acknowledgements(
        [30], acknowledged_werks_mk=acknowledge_werks_file
    )
    # let's update to 2.6.0:
    save_werks_to_site(WERKS_260)
    update_config()
    cmk.utils.werks.acknowledgement.save_acknowledgements(
        [50], acknowledged_werks_mk=acknowledge_werks_file
    )
    werks = werks_load()
    assert set(werks) == {60}

    # the user acknowledges the last 2.5.0 werk, and updates again
    # we expect that the site werks file is now empty
    cmk.utils.werks.acknowledgement.save_acknowledgements(
        [50, 60], acknowledged_werks_mk=acknowledge_werks_file
    )
    update_config()
    assert unacknowledged_werks_file.read_text().strip() == "{}"
