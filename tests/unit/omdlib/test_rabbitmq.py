#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.rabbitmq import write_rabbitmq_default_conf, write_rabbitmq_management_port_conf


def test_write_rabbitmq_default_conf_single_addr(tmp_path: Path) -> None:
    (tmp_path / "etc/rabbitmq/conf.d").mkdir(parents=True)
    write_rabbitmq_default_conf(str(tmp_path), "192.168.1.1", "5671")
    content = (tmp_path / "etc/rabbitmq/conf.d/01-default.conf").read_text()
    assert "# Port and IP addresses set by `omd config` hooks `RABBITMQ_ONLY_FROM` and" in content
    assert "# `RABBITMQ_PORT`. Better do not edit manually." in content
    assert "listeners.ssl.1 = 192.168.1.1:5671" in content


def test_write_rabbitmq_default_conf_multiple_addrs(tmp_path: Path) -> None:
    (tmp_path / "etc/rabbitmq/conf.d").mkdir(parents=True)
    write_rabbitmq_default_conf(str(tmp_path), "10.0.0.1 10.0.0.2", "5671")
    content = (tmp_path / "etc/rabbitmq/conf.d/01-default.conf").read_text()
    assert "listeners.ssl.1 = 10.0.0.1:5671" in content
    assert "listeners.ssl.2 = 10.0.0.2:5671" in content


def test_write_rabbitmq_default_conf_empty_only_from(tmp_path: Path) -> None:
    (tmp_path / "etc/rabbitmq/conf.d").mkdir(parents=True)
    write_rabbitmq_default_conf(str(tmp_path), "", "5671")
    content = (tmp_path / "etc/rabbitmq/conf.d/01-default.conf").read_text()
    assert "listeners.ssl" not in content


def test_write_rabbitmq_default_conf_overwrites(tmp_path: Path) -> None:
    (tmp_path / "etc/rabbitmq/conf.d").mkdir(parents=True)
    write_rabbitmq_default_conf(str(tmp_path), "192.168.1.1", "5671")
    write_rabbitmq_default_conf(str(tmp_path), "192.168.1.1", "5672")
    content = (tmp_path / "etc/rabbitmq/conf.d/01-default.conf").read_text()
    assert "5672" in content
    assert "5671" not in content


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
