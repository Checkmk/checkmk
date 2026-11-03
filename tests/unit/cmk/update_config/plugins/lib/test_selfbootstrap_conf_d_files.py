#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.ccc import store
from cmk.update_config.plugins.lib.selfbootstrap_conf_d_files import (
    ExtendOnlyFile,
    resave_extend_only_files,
)
from tests.unit.cmk.update_config.plugins.actions.selfbootstrap_conf_d_helpers import (
    make_wato_dir,
)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(name="wato_dir")
def wato_dir_fixture() -> Iterator[Path]:
    yield from make_wato_dir()


def _recording_file(name: str, calls: list[bool]) -> ExtendOnlyFile:
    return ExtendOnlyFile(name=name, resave=calls.append)


def test_skips_a_self_bootstrapping_file(wato_dir: Path) -> None:
    store.save_to_mk_file(wato_dir / "a.mk", key="x", value={})
    calls: list[bool] = []

    resave_extend_only_files([_recording_file("a.mk", calls)], pprint_value=False, logger=_LOGGER)

    assert calls == []


def test_skips_a_file_that_only_assigns(wato_dir: Path) -> None:
    (wato_dir / "a.mk").write_text("x = {'a': 1}\n")
    calls: list[bool] = []

    resave_extend_only_files([_recording_file("a.mk", calls)], pprint_value=False, logger=_LOGGER)

    assert calls == []


def test_skips_a_missing_file(wato_dir: Path) -> None:
    calls: list[bool] = []

    resave_extend_only_files([_recording_file("a.mk", calls)], pprint_value=False, logger=_LOGGER)

    assert calls == []
    assert list(wato_dir.iterdir()) == []


def test_a_failing_resave_is_reported_and_the_others_continue(
    wato_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (wato_dir / "broken.mk").write_text("x.update({})\n")
    (wato_dir / "other.mk").write_text("y.update({})\n")
    calls: list[bool] = []

    def fail(_pprint_value: bool) -> None:
        raise ValueError("boom")

    resave_extend_only_files(
        [ExtendOnlyFile(name="broken.mk", resave=fail), _recording_file("other.mk", calls)],
        pprint_value=False,
        logger=_LOGGER,
    )

    assert [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING] == [
        f"{wato_dir / 'broken.mk'}: left unchanged, it cannot be re-saved: boom"
    ]
    assert calls == [False]
