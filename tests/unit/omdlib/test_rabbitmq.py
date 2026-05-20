#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.rabbitmq import write_rabbitmq_management_port_conf


def test_write_rabbitmq_management_port_conf(tmp_path: Path) -> None:
    (tmp_path / "etc/rabbitmq/conf.d").mkdir(parents=True)
    write_rabbitmq_management_port_conf(str(tmp_path), "15671")
    content = (tmp_path / "etc/rabbitmq/conf.d/02-management-port.conf").read_text()
    assert "# Port set by `omd config` hook `RABBITMQ_MANAGEMENT_PORT`" in content
    assert "management.ssl.port = 15671" in content


def test_write_rabbitmq_management_port_conf_overwrites(tmp_path: Path) -> None:
    (tmp_path / "etc/rabbitmq/conf.d").mkdir(parents=True)
    write_rabbitmq_management_port_conf(str(tmp_path), "15671")
    write_rabbitmq_management_port_conf(str(tmp_path), "15672")
    content = (tmp_path / "etc/rabbitmq/conf.d/02-management-port.conf").read_text()
    assert "15672" in content
    assert "15671" not in content
