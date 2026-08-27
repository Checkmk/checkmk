#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import pytest
from marshmallow_oneofschema.one_of_schema import OneOfSchema

from cmk.ccc.site import SiteId
from cmk.gui.openapi.endpoints.global_settings.schemas import (
    CAInputSchema,
    FileUploadSchema,
    IconSchema,
)
from cmk.gui.watolib.config_domain_name import ABCConfigDomain, get_config_domain, GUI
from cmk.gui.watolib.site_changes import SiteChanges
from tests.testlib.rest_api_client import ClientRegistry

LOCAL_SITE = "NO_SITE"

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


@pytest.fixture(name="user_without_global_permission")
def fixture_user_without_global_permission(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin", "new_role_id": "no_globals"})
    clients.UserRole.edit(role_id="no_globals", body={"new_permissions": {"wato.global": "no"}})
    clients.User.create(
        username="no_globals",
        fullname="no_globals",
        roles=["no_globals"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
    )
    clients.GlobalSetting.set_credentials("no_globals", "supersecretish")


def test_show_factory_setting(clients: ClientRegistry) -> None:
    resp = clients.GlobalSetting.get(INT_VAR)
    assert resp.json == {"varname": INT_VAR, "value": INT_DEFAULT, "is_default": True}
    assert resp.headers["ETag"]


def test_unknown_variable_404(clients: ClientRegistry) -> None:
    clients.GlobalSetting.get("no_such_variable", expect_ok=False).assert_status_code(404)


def test_variable_outside_the_global_settings_404(clients: ClientRegistry) -> None:
    """default_language is registered but declared in_global_settings=False."""
    clients.GlobalSetting.get("default_language", expect_ok=False).assert_status_code(404)


def _changes_of(site_id: str) -> list[str]:
    return [
        change["text"]
        for change in SiteChanges(SiteId(site_id)).read()
        if change["action_name"] == "edit-configvar"
    ]


def test_update_clears_is_default(clients: ClientRegistry) -> None:
    assert clients.GlobalSetting.update(INT_VAR, 42).json == {
        "varname": INT_VAR,
        "value": 42,
        "is_default": False,
    }
    assert clients.GlobalSetting.get(INT_VAR).json["is_default"] is False


def test_update_to_the_default_value_still_clears_is_default(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, INT_DEFAULT)
    resp = clients.GlobalSetting.get(INT_VAR)
    assert resp.json["value"] == INT_DEFAULT
    assert resp.json["is_default"] is False


@pytest.mark.parametrize("varname", ["log_levels", INT_VAR])
def test_the_shown_value_can_be_sent_back_unchanged(clients: ClientRegistry, varname: str) -> None:
    shown = clients.GlobalSetting.get(varname).json["value"]
    assert clients.GlobalSetting.update(varname, shown).json["value"] == shown


def test_update_with_a_rejected_value_400(clients: ClientRegistry) -> None:
    resp = clients.GlobalSetting.update(INT_VAR, "not a number", expect_ok=False)
    resp.assert_status_code(400)
    assert clients.GlobalSetting.get(INT_VAR).json["is_default"] is True


def test_delete_resets_to_the_factory_setting(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)
    clients.GlobalSetting.delete(INT_VAR).assert_status_code(204)
    assert clients.GlobalSetting.get(INT_VAR).json == {
        "varname": INT_VAR,
        "value": INT_DEFAULT,
        "is_default": True,
    }


def test_delete_of_an_unconfigured_variable_is_a_no_op(clients: ClientRegistry) -> None:
    clients.GlobalSetting.delete(INT_VAR).assert_status_code(204)
    assert clients.GlobalSetting.get(INT_VAR).json["is_default"] is True
    assert _changes_of(LOCAL_SITE) == []


def test_update_records_a_pending_change(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)
    assert _changes_of(LOCAL_SITE) == [f"Changed global configuration variable {INT_VAR}."]


def test_delete_records_a_pending_change(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)
    clients.GlobalSetting.delete(INT_VAR)
    assert _changes_of(LOCAL_SITE)[-1] == (
        f"Resetted configuration variable {INT_VAR} to its default."
    )


def test_update_needs_a_matching_etag(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, 42, etag=None, expect_ok=False).assert_status_code(428)
    clients.GlobalSetting.update(
        INT_VAR, 42, etag="invalid_etag", expect_ok=False
    ).assert_status_code(412)
    clients.GlobalSetting.update(INT_VAR, 42, etag="valid_etag").assert_status_code(200)


def test_delete_needs_a_matching_etag(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)
    clients.GlobalSetting.delete(INT_VAR, etag=None, expect_ok=False).assert_status_code(428)
    clients.GlobalSetting.delete(INT_VAR, etag="invalid_etag", expect_ok=False).assert_status_code(
        412
    )
    clients.GlobalSetting.delete(INT_VAR, etag="valid_etag").assert_status_code(204)


def test_an_update_invalidates_a_previously_read_etag(clients: ClientRegistry) -> None:
    stale = clients.GlobalSetting.get(INT_VAR).headers["ETag"]
    clients.GlobalSetting.update(INT_VAR, 42)
    clients.GlobalSetting.request(
        "put",
        url=f"/objects/global_setting/{INT_VAR}",
        body={"value": 43},
        headers={"If-Match": stale},
        expect_ok=False,
    ).assert_status_code(412)


def test_the_etag_returned_by_an_update_is_still_valid(clients: ClientRegistry) -> None:
    """The update builds its response from the value it just wrote instead of reading it
    back, so that value has to agree with what a later read reports."""
    etag = clients.GlobalSetting.update(INT_VAR, 42).headers["ETag"]
    assert clients.GlobalSetting.get(INT_VAR).headers["ETag"] == etag
    clients.GlobalSetting.request(
        "put",
        url=f"/objects/global_setting/{INT_VAR}",
        body={"value": 43},
        headers={"If-Match": etag},
    ).assert_status_code(200)


def test_setting_a_variable_to_its_default_value_changes_the_etag(
    clients: ClientRegistry,
) -> None:
    """is_default is part of the tag, so an explicit write of the default value still moves it."""
    stale = clients.GlobalSetting.get(INT_VAR).headers["ETag"]
    clients.GlobalSetting.update(INT_VAR, INT_DEFAULT)
    assert clients.GlobalSetting.get(INT_VAR).headers["ETag"] != stale


@pytest.mark.usefixtures("user_without_global_permission")
def test_central_scope_needs_the_global_permission(clients: ClientRegistry) -> None:
    clients.GlobalSetting.get(INT_VAR, expect_ok=False).assert_status_code(403)
    clients.GlobalSetting.update(INT_VAR, 42, expect_ok=False).assert_status_code(403)
    clients.GlobalSetting.delete(INT_VAR, expect_ok=False).assert_status_code(403)


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
