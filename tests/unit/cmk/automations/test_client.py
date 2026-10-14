#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.automations import client


def test_an_invalid_version_is_rejected_before_contacting_the_helper(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "sys.argv", ["cmk-automation-client", "--for-cmk-version", "foo", "restart"]
    )
    # No OMD_ROOT and no helper: getting past argument parsing would fail differently.
    monkeypatch.delenv("OMD_ROOT", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        client.main()

    assert exc_info.value.code == 2
    assert 'argument --for-cmk-version: Invalid version string "foo"' in capsys.readouterr().err
