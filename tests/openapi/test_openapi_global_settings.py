#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import pytest
from marshmallow_oneofschema.one_of_schema import OneOfSchema

from cmk.gui.openapi.endpoints.global_settings.schemas import (
    CAInputSchema,
    FileUploadSchema,
    IconSchema,
)
from cmk.gui.watolib.config_domain_name import ABCConfigDomain, get_config_domain, GUI
from tests.testlib.rest_api_client import ClientRegistry

# An integer, so that a test can state an expected value without depending on how a form
# spec encodes a more complex one.
INT_VAR = "wato_max_snapshots"
INT_DEFAULT = 50


@pytest.fixture(autouse=True)
def patch_factory_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_all_default_globals() runs an automation and reads files only a real site has."""
    monkeypatch.setattr(
        ABCConfigDomain,
        "get_all_default_globals",
        classmethod(
            lambda cls: {
                **get_config_domain(GUI).default_globals(),
                **get_config_domain("ec").default_globals(),
            }
        ),
    )


@pytest.fixture(autouse=True)
def sample_ca_certificates() -> None:
    """ConfigDomainCACertificates.save() - which every write triggers - trips over its own
    fallback when the variable is unset. A real site always has it from the sample config."""
    config_file = get_config_domain("ca-certificates").config_file(site_specific=False)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        "trusted_certificate_authorities = {'use_system_wide_cas': False, 'trusted_cas': []}\n"
    )


def test_show_factory_setting(clients: ClientRegistry) -> None:
    resp = clients.GlobalSetting.get(INT_VAR)
    assert resp.json == {"varname": INT_VAR, "value": INT_DEFAULT, "is_default": True}
    assert resp.headers["ETag"]


def test_unknown_variable_404(clients: ClientRegistry) -> None:
    clients.GlobalSetting.get("no_such_variable", expect_ok=False).assert_status_code(404)


def test_variable_outside_the_global_settings_404(clients: ClientRegistry) -> None:
    """default_language is registered but declared in_global_settings=False."""
    clients.GlobalSetting.get("default_language", expect_ok=False).assert_status_code(404)


@pytest.mark.parametrize(
    "schema, data",
    [
        (IconSchema(), {"type": "enabled", "icon": "delete"}),
        (IconSchema(), {"type": "enabled", "icon": "delete", "emblem": "search"}),
        (IconSchema(), {"type": "disabled"}),
        (CAInputSchema(), {"type": "enabled", "address": "localhost", "port": 443}),
        (CAInputSchema(), {"type": "disabled"}),
        (
            FileUploadSchema(),
            {"type": "file", "name": "my_file", "content": "foobar", "mimetype": "text/plain"},
        ),
        (FileUploadSchema(), {"type": "raw", "raw_value": "foobar"}),
        (FileUploadSchema(), {"type": "disabled"}),
    ],
)
def test_global_settings_oneofschemas(schema: OneOfSchema, data: dict) -> None:  # type: ignore[misc]
    assert schema.load(data) == data
    assert schema.dump(data) == data
