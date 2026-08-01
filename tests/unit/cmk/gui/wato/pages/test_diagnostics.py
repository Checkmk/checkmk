#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import tarfile
from pathlib import Path

from cmk.gui.wato.pages.diagnostics import _join_sub_tars


def _make_sub_tar(path: Path, content: Path) -> Path:
    with tarfile.open(name=path, mode="w:gz") as tar:
        tar.add(content, arcname=content.name, recursive=True)
    return path


def test_join_sub_tars_keeps_symlinks(tmp_path: Path) -> None:
    # Diagnostics dumps contain the operating system's Apache configuration
    # verbatim, which includes the symlinks below /etc/apache2/conf-enabled.
    source = tmp_path / "source" / "conf"
    source.mkdir(parents=True)
    (source / "charset.conf").write_text("AddDefaultCharset UTF-8\n")
    (source / "charset-enabled.conf").symlink_to("charset.conf")

    sub_tars = [
        str(_make_sub_tar(tmp_path / "sub1.tar.gz", source)),
        str(_make_sub_tar(tmp_path / "sub2.tar.gz", source)),
    ]

    diagnostics_dir = tmp_path / "dump"
    diagnostics_dir.mkdir()

    joined = _join_sub_tars(diagnostics_dir, sub_tars)

    with tarfile.open(name=joined, mode="r:gz") as tar:
        members = {member.name: member for member in tar.getmembers()}
        assert sorted(members) == [
            "conf",
            "conf/charset-enabled.conf",
            "conf/charset.conf",
        ]
        assert members["conf"].isdir()
        assert members["conf/charset-enabled.conf"].issym()
        assert members["conf/charset-enabled.conf"].linkname == "charset.conf"
        assert (regular := tar.extractfile(members["conf/charset.conf"])) is not None
        assert regular.read() == b"AddDefaultCharset UTF-8\n"
