#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.jaeger import write_jaeger_admin_port_conf


def test_write_jaeger_admin_port_conf(tmp_path: Path) -> None:
    (tmp_path / "etc/jaeger").mkdir(parents=True)
    write_jaeger_admin_port_conf(str(tmp_path), "14269")
    content = (tmp_path / "etc/jaeger/omd-admin-port.yaml").read_text()
    assert "# Written by TRACE_JAEGER_ADMIN_PORT hook" in content
    assert "port: 14269" in content
    assert 'host: "[::1]"' in content


def test_write_jaeger_admin_port_conf_overwrites(tmp_path: Path) -> None:
    (tmp_path / "etc/jaeger").mkdir(parents=True)
    write_jaeger_admin_port_conf(str(tmp_path), "14269")
    write_jaeger_admin_port_conf(str(tmp_path), "14270")
    content = (tmp_path / "etc/jaeger/omd-admin-port.yaml").read_text()
    assert "14270" in content
    assert "14269" not in content
