#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.testlib.aws_v2.fake_sts import FakeSts, running_fake_sts


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def patch_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))


@pytest.fixture(name="fake_sts")
def _fake_sts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeSts]:
    """Route STS and Organizations calls to a fake and hide the credentials of the test host."""
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "does_not_exist"))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "does_not_exist"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    for name in ("AWS_PROFILE", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    with running_fake_sts() as sts:
        monkeypatch.setenv("AWS_ENDPOINT_URL_STS", sts.url)
        monkeypatch.setenv("AWS_ENDPOINT_URL_ORGANIZATIONS", sts.url)
        yield sts
