#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.gui.wato._omd_configuration import ConfigDomainApache
from cmk.utils import paths


def test_apache_default_is_read_from_the_directive_with_the_exact_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(paths, "omd_root", tmp_path)
    (tmp_path / "etc/apache/conf.d").mkdir(parents=True)
    (tmp_path / "etc/apache/apache.conf").write_text("MaxClientsFoo 10\nMaxClients\n")
    (tmp_path / "etc/apache/conf.d/tuning.conf").write_text("MaxClients 42\n")

    assert ConfigDomainApache().default_globals() == {
        "apache_process_tuning": {"number_of_processes": 42}
    }
