#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.jaeger import write_jaeger_admin_port_conf, write_jaeger_ui_port_conf


def test_write_jaeger_admin_port_conf(tmp_path: Path) -> None:
    (tmp_path / "etc/jaeger").mkdir(parents=True)
    write_jaeger_admin_port_conf(str(tmp_path), "14269")
    content = (tmp_path / "etc/jaeger/omd-admin-port.yaml").read_text()
    assert "# Written by TRACE_JAEGER_ADMIN_PORT hook" in content
    assert "port: 14269" in content
    assert 'host: "[::1]"' in content


def test_write_jaeger_ui_port_conf(tmp_path: Path) -> None:
    (tmp_path / "etc/jaeger").mkdir(parents=True)
    write_jaeger_ui_port_conf(str(tmp_path), "mysite", "16686")
    apache = (tmp_path / "etc/jaeger/apache.conf").read_text()
    assert "# Written by TRACE_JAEGER_UI_PORT hook" in apache
    assert "/omd/sites/mysite/lib/apache/modules/mod_proxy.so" in apache
    assert '"http://[::1]:16686/mysite/jaeger"' in apache
    query = (tmp_path / "etc/jaeger/omd-query-port.yaml").read_text()
    assert "# Written by TRACE_JAEGER_UI_PORT hook" in query
    assert 'endpoint: "[::1]:16686"' in query


def test_write_jaeger_ui_port_conf_overwrites(tmp_path: Path) -> None:
    (tmp_path / "etc/jaeger").mkdir(parents=True)
    write_jaeger_ui_port_conf(str(tmp_path), "mysite", "16686")
    write_jaeger_ui_port_conf(str(tmp_path), "mysite", "16687")
    apache = (tmp_path / "etc/jaeger/apache.conf").read_text()
    assert "16687" in apache
    assert "16686" not in apache


def test_write_jaeger_admin_port_conf_overwrites(tmp_path: Path) -> None:
    (tmp_path / "etc/jaeger").mkdir(parents=True)
    write_jaeger_admin_port_conf(str(tmp_path), "14269")
    write_jaeger_admin_port_conf(str(tmp_path), "14270")
    content = (tmp_path / "etc/jaeger/omd-admin-port.yaml").read_text()
    assert "14270" in content
    assert "14269" not in content
