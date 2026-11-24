#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

from cmk.ccc.general_version_infos import main


def test_main_prints_the_version_infos_of_the_site_as_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "etc" / "omd").mkdir(parents=True)
    (tmp_path / "etc" / "omd" / "site.conf").write_text("CONFIG_CORE='nagios'\n", encoding="utf-8")
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))

    main()

    assert json.loads(capsys.readouterr().out)["core"] == "nagios"


def test_main_outside_of_a_site_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMD_ROOT", raising=False)

    with pytest.raises(RuntimeError, match="OMD_ROOT"):
        main()
