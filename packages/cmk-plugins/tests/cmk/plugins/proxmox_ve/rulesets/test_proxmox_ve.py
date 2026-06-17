#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.proxmox_ve.rulesets.proxmox_ve import (
    connection_elements,
    credentials_elements,
    form_special_agents_proxmox_ve,
)


def test_credentials_elements_required() -> None:
    elements = credentials_elements(required=True)
    assert set(elements) == {"username", "password"}
    assert all(element.required for element in elements.values())


def test_credentials_elements_optional_by_default() -> None:
    assert all(not element.required for element in credentials_elements().values())


def test_connection_elements_keys() -> None:
    assert set(connection_elements()) == {
        "port",
        "host",
        "no_cert_check",
        "timeout",
        "log_cutoff_weeks",
    }


def test_form_special_agents_proxmox_ve_composes_shared_elements() -> None:
    elements = form_special_agents_proxmox_ve().elements
    assert set(elements) == {
        "username",
        "password",
        "port",
        "host",
        "no_cert_check",
        "timeout",
        "log_cutoff_weeks",
    }
    # In the plain ruleset the credentials remain optional.
    assert not elements["username"].required
    assert not elements["password"].required
