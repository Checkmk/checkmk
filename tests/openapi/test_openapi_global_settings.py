#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import override

import pytest
from marshmallow_oneofschema.one_of_schema import OneOfSchema

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.gui.config import Config
from cmk.gui.customer import (
    customer_api_registry,
    CustomerAPIStub,
    CustomerIdOrGlobal,
    SCOPE_GLOBAL,
)
from cmk.gui.form_specs.unstable.legacy_valuespec import LegacyValueSpec
from cmk.gui.mkeventd.config_domain import ConfigDomainEventConsole
from cmk.gui.openapi.api_endpoints.site_management.models.config_example import (
    default_config_example,
)
from cmk.gui.openapi.endpoints.global_settings.schemas import (
    CAInputSchema,
    FileUploadSchema,
    IconSchema,
)
from cmk.gui.type_defs import ReadOnlySpec
from cmk.gui.valuespec import TextInput
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    CA_CERTIFICATES,
    config_variable_registry,
    ConfigVariable,
    get_config_domain,
    GUI,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupUserInterface
from cmk.gui.watolib.piggyback_hub import CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT
from cmk.gui.watolib.site_changes import SiteChanges
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import BooleanChoice, FormSpec, Password
from tests.testlib.gui.web_test_app import SetConfig
from tests.testlib.rest_api_client import ClientRegistry

LOCAL_SITE = "NO_SITE"

# An integer, so that a test can state an expected value without depending on how a form
# spec encodes a more complex one.
INT_VAR = "wato_max_snapshots"
INT_DEFAULT = 50

EXECUTABLES_VAR = "actions"


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def patch_factory_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_all_default_globals() runs an automation and reads files only a real site has."""
    monkeypatch.setattr(
        ABCConfigDomain,
        "get_all_default_globals",
        classmethod(
            lambda cls: {  # noqa: ARG005
                **get_config_domain(GUI).default_globals(),
                **get_config_domain("ec").default_globals(),
                **get_config_domain(CA_CERTIFICATES).default_globals(),
            }
        ),
    )


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def sample_ca_certificates() -> None:
    """ConfigDomainCACertificates.save() - which every write triggers - would otherwise fall
    back to its default and scan the system-wide CAs. A real site always has the variable
    from the sample config."""
    config_file = get_config_domain("ca-certificates").config_file(site_specific=False)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        "trusted_certificate_authorities = {'use_system_wide_cas': False, 'trusted_cas': []}\n"
    )


def _create_remote_site(clients: ClientRegistry, site_id: str, replicate_ec: bool) -> str:
    config = default_config_example()
    config["basic_settings"]["site_id"] = site_id
    config["configuration_connection"]["replicate_event_console"] = replicate_ec
    clients.SiteManagement.create(site_config=config)
    return site_id


@pytest.fixture(name="remote_site")
def fixture_remote_site(clients: ClientRegistry) -> str:
    """The site scope needs a distributed setup, see the negative test below."""
    return _create_remote_site(clients, "site_id_1", replicate_ec=True)


@pytest.fixture(name="site_without_event_console")
def fixture_site_without_event_console(clients: ClientRegistry) -> str:
    return _create_remote_site(clients, "site_without_ec", replicate_ec=False)


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


@pytest.fixture(name="user_without_event_console_permission")
def fixture_user_without_event_console_permission(clients: ClientRegistry) -> None:
    """Holds the general global-settings permission but not the Event Console's own."""
    clients.UserRole.clone(body={"role_id": "admin", "new_role_id": "no_event_console"})
    clients.UserRole.edit(
        role_id="no_event_console", body={"new_permissions": {"mkeventd.config": "no"}}
    )
    clients.User.create(
        username="no_event_console",
        fullname="no_event_console",
        roles=["no_event_console"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
    )
    clients.GlobalSetting.set_credentials("no_event_console", "supersecretish")


@pytest.fixture(name="user_without_executables_permission")
def fixture_user_without_executables_permission(clients: ClientRegistry) -> None:
    clients.UserRole.clone(body={"role_id": "admin", "new_role_id": "no_executables"})
    clients.UserRole.edit(
        role_id="no_executables",
        body={"new_permissions": {"wato.add_or_modify_executables": "no"}},
    )
    clients.User.create(
        username="no_executables",
        fullname="no_executables",
        roles=["no_executables"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
    )
    clients.GlobalSetting.set_credentials("no_executables", "supersecretish")


class _SiteOfACustomer(CustomerAPIStub):
    """Multi-tenancy as an edition with customers implements it."""

    @classmethod
    @override
    def current_customer(cls, config: Config) -> CustomerIdOrGlobal:
        return "customer_a"

    @classmethod
    @override
    def is_global(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return customer_id is SCOPE_GLOBAL

    @classmethod
    @override
    def is_provider(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return customer_id == "provider"


@contextmanager
def _site_of_a_customer(local_edition: Edition) -> Iterator[None]:
    ident = str(local_edition)
    previous = customer_api_registry[ident]
    customer_api_registry.register(_SiteOfACustomer(ident))
    try:
        yield
    finally:
        customer_api_registry.register(previous)


def _register_variable(
    monkeypatch: pytest.MonkeyPatch,
    varname: str,
    domain: type[ABCConfigDomain],
    form_spec: FormSpec,
    default: object,
) -> Iterator[str]:
    defaults = ABCConfigDomain.get_all_default_globals()
    monkeypatch.setattr(
        ABCConfigDomain,
        "get_all_default_globals",
        classmethod(lambda cls: {**defaults, varname: default}),  # noqa: ARG005
    )
    config_variable_registry.register(
        ConfigVariable(
            group=ConfigVariableGroupUserInterface,
            primary_domain=domain,
            ident=varname,
            form_spec=lambda context: form_spec,  # noqa: ARG005
        )
    )
    yield varname
    config_variable_registry.unregister(varname)


@pytest.fixture(name="secret_var")
def fixture_secret_var(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    yield from _register_variable(
        monkeypatch, "test_secret", ConfigDomainGUI, Password(title=Title("Secret")), None
    )


@pytest.fixture(name="event_console_var")
def fixture_event_console_var(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    yield from _register_variable(
        monkeypatch,
        "test_ec_setting",
        ConfigDomainEventConsole,
        BooleanChoice(title=Title("Event Console toggle")),
        False,
    )


@pytest.fixture(name="piggyback_hub_var")
def fixture_piggyback_hub_var(monkeypatch: pytest.MonkeyPatch) -> str:
    defaults = ABCConfigDomain.get_all_default_globals()
    monkeypatch.setattr(
        ABCConfigDomain,
        "get_all_default_globals",
        classmethod(lambda cls: {**defaults, CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT: False}),  # noqa: ARG005
    )
    return CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT


@pytest.fixture(name="legacy_valuespec_var")
def fixture_legacy_valuespec_var(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    yield from _register_variable(
        monkeypatch,
        "test_legacy_valuespec",
        ConfigDomainGUI,
        LegacyValueSpec.wrap(TextInput(title="Legacy text")),
        "",
    )


@pytest.fixture(name="var_without_factory_default")
def fixture_var_without_factory_default() -> Iterator[str]:
    varname = "test_no_default"
    config_variable_registry.register(
        ConfigVariable(
            group=ConfigVariableGroupUserInterface,
            primary_domain=ConfigDomainGUI,
            ident=varname,
            form_spec=lambda context: BooleanChoice(),  # noqa: ARG005
        )
    )
    yield varname
    config_variable_registry.unregister(varname)


def test_show_factory_setting(clients: ClientRegistry) -> None:
    resp = clients.GlobalSetting.get(INT_VAR)
    assert resp.json == {"varname": INT_VAR, "value": INT_DEFAULT, "origin": "factory"}
    assert resp.headers["ETag"]


def test_unknown_variable_404(clients: ClientRegistry) -> None:
    clients.GlobalSetting.get("no_such_variable", expect_ok=False).assert_status_code(404)


def test_variable_outside_the_global_settings_404(clients: ClientRegistry) -> None:
    """default_language is registered but declared in_global_settings=False."""
    clients.GlobalSetting.get("default_language", expect_ok=False).assert_status_code(404)


def test_variable_without_a_factory_default_404(
    clients: ClientRegistry, var_without_factory_default: str
) -> None:
    clients.GlobalSetting.get(var_without_factory_default, expect_ok=False).assert_status_code(404)


def _changes_of(site_id: str) -> list[str]:
    return [
        change["text"]
        for change in SiteChanges(SiteId(site_id)).read()
        if change["action_name"] == "edit-configvar"
    ]


def test_update_moves_the_origin_to_the_global_layer(clients: ClientRegistry) -> None:
    assert clients.GlobalSetting.update(INT_VAR, 42).json == {
        "varname": INT_VAR,
        "value": 42,
        "origin": "global",
    }
    assert clients.GlobalSetting.get(INT_VAR).json["origin"] == "global"


def test_update_to_the_default_value_still_moves_the_origin(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, INT_DEFAULT)
    resp = clients.GlobalSetting.get(INT_VAR)
    assert resp.json["value"] == INT_DEFAULT
    assert resp.json["origin"] == "global"


@pytest.mark.parametrize("varname", ["log_levels", INT_VAR])
def test_the_shown_value_can_be_sent_back_unchanged(clients: ClientRegistry, varname: str) -> None:
    shown = clients.GlobalSetting.get(varname).json["value"]
    assert clients.GlobalSetting.update(varname, shown).json["value"] == shown


def test_update_with_a_rejected_value_400(clients: ClientRegistry) -> None:
    resp = clients.GlobalSetting.update(INT_VAR, "not a number", expect_ok=False)
    resp.assert_status_code(400)
    assert clients.GlobalSetting.get(INT_VAR).json["origin"] == "factory"


def test_delete_resets_to_the_factory_setting(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)
    clients.GlobalSetting.delete(INT_VAR).assert_status_code(204)
    assert clients.GlobalSetting.get(INT_VAR).json == {
        "varname": INT_VAR,
        "value": INT_DEFAULT,
        "origin": "factory",
    }


def test_delete_of_an_unconfigured_variable_is_a_no_op(clients: ClientRegistry) -> None:
    clients.GlobalSetting.delete(INT_VAR).assert_status_code(204)
    assert clients.GlobalSetting.get(INT_VAR).json["origin"] == "factory"
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


def _audit_diffs() -> list[str | None]:
    return [entry.diff_text for entry in AuditLogStore().read() if entry.action == "edit-configvar"]


def test_update_records_the_audit_description_the_page_records(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)
    assert _audit_diffs() == [f'Attribute "{INT_VAR}" with value 42 added.']


def test_a_further_update_reads_as_a_value_change(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)
    clients.GlobalSetting.update(INT_VAR, 7)
    assert _audit_diffs()[-1] == f'Value of "{INT_VAR}" changed from 42 to 7.'


def test_delete_records_the_audit_description_the_page_records(clients: ClientRegistry) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)
    clients.GlobalSetting.delete(INT_VAR)
    assert _audit_diffs()[-1] == f'Attribute "{INT_VAR}" with value 42 removed.'


def test_a_secret_is_redacted_in_the_audit_description(
    clients: ClientRegistry, secret_var: str
) -> None:
    clients.GlobalSetting.update(secret_var, ["explicit_password", "", "hunter2", False])
    diff_text = _audit_diffs()[-1]
    assert diff_text is not None
    assert "hunter2" not in diff_text
    assert "Redacted secrets changed." in diff_text


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


def test_a_legacy_valuespec_does_not_move_the_etag_of_its_setting(
    clients: ClientRegistry, legacy_valuespec_var: str
) -> None:
    """A legacy valuespec renders a fresh element ID into the form spec representation of the
    value on every request. A tag taken from that representation never matches the next one,
    leaving the setting readable but no longer writable."""
    etag = clients.GlobalSetting.get(legacy_valuespec_var).headers["ETag"]
    assert clients.GlobalSetting.get(legacy_valuespec_var).headers["ETag"] == etag


def test_setting_a_variable_to_its_default_value_changes_the_etag(
    clients: ClientRegistry,
) -> None:
    """The origin is part of the tag, so an explicit write of the default value still moves it."""
    stale = clients.GlobalSetting.get(INT_VAR).headers["ETag"]
    clients.GlobalSetting.update(INT_VAR, INT_DEFAULT)
    assert clients.GlobalSetting.get(INT_VAR).headers["ETag"] != stale


@pytest.mark.usefixtures("user_without_global_permission")
def test_central_scope_needs_the_global_permission(clients: ClientRegistry) -> None:
    clients.GlobalSetting.get(INT_VAR, expect_ok=False).assert_status_code(403)
    clients.GlobalSetting.update(INT_VAR, 42, expect_ok=False).assert_status_code(403)
    clients.GlobalSetting.delete(INT_VAR, expect_ok=False).assert_status_code(403)


@pytest.mark.usefixtures("user_without_global_permission")
def test_site_scope_needs_the_global_permission(clients: ClientRegistry, remote_site: str) -> None:
    clients.GlobalSetting.get_site(remote_site, INT_VAR, expect_ok=False).assert_status_code(403)
    clients.GlobalSetting.update_site(remote_site, INT_VAR, 42, expect_ok=False).assert_status_code(
        403
    )
    clients.GlobalSetting.delete_site(remote_site, INT_VAR, expect_ok=False).assert_status_code(403)


@pytest.mark.usefixtures("user_without_event_console_permission")
def test_an_event_console_setting_needs_the_event_console_permission(
    clients: ClientRegistry, event_console_var: str
) -> None:
    """wato.global does not reach an Event Console variable.

    An ordinary variable is exercised afterwards with the same user on the same
    route, so the refusals cannot be read as that user having no access to the
    endpoints at all.
    """
    clients.GlobalSetting.get(event_console_var, expect_ok=False).assert_status_code(403)
    clients.GlobalSetting.update(event_console_var, True, expect_ok=False).assert_status_code(403)
    clients.GlobalSetting.delete(event_console_var, expect_ok=False).assert_status_code(403)

    assert clients.GlobalSetting.get(INT_VAR).json["value"] == INT_DEFAULT
    assert clients.GlobalSetting.update(INT_VAR, 42).json["value"] == 42


@pytest.mark.usefixtures("user_without_global_permission")
def test_an_event_console_setting_does_not_need_the_general_permission(
    clients: ClientRegistry, event_console_var: str
) -> None:
    """mkeventd.config alone does reach an Event Console variable.

    The permission demanded is the one the variable's own configuration domain
    declares, so wato.global — which every ordinary variable requires — is not
    required here.
    """
    assert clients.GlobalSetting.get(event_console_var).json["value"] is False
    assert clients.GlobalSetting.update(event_console_var, True).json["value"] is True
    clients.GlobalSetting.delete(event_console_var)


@pytest.mark.usefixtures("user_without_event_console_permission")
def test_an_event_console_site_override_needs_the_event_console_permission(
    clients: ClientRegistry, remote_site: str, event_console_var: str
) -> None:
    """A site override asks for the variable's own permission, the same as the central value.

    An ordinary variable is read afterwards on the same route, so the refusals cannot be
    read as that user having no access to the site scope at all.
    """
    clients.GlobalSetting.get_site(
        remote_site, event_console_var, expect_ok=False
    ).assert_status_code(403)
    clients.GlobalSetting.update_site(
        remote_site, event_console_var, True, expect_ok=False
    ).assert_status_code(403)
    clients.GlobalSetting.delete_site(
        remote_site, event_console_var, expect_ok=False
    ).assert_status_code(403)

    assert clients.GlobalSetting.get_site(remote_site, INT_VAR).json["value"] == INT_DEFAULT


@pytest.mark.usefixtures("user_without_global_permission")
def test_an_event_console_site_override_does_not_need_the_general_permission(
    clients: ClientRegistry, remote_site: str, event_console_var: str
) -> None:
    assert (
        clients.GlobalSetting.update_site(remote_site, event_console_var, True).json["value"]
        is True
    )
    clients.GlobalSetting.delete_site(remote_site, event_console_var)


@pytest.mark.usefixtures("user_without_executables_permission")
def test_the_event_console_actions_need_the_executables_permission(
    clients: ClientRegistry,
) -> None:
    clients.GlobalSetting.get(EXECUTABLES_VAR, expect_ok=False).assert_status_code(403)


@pytest.mark.usefixtures("user_without_global_permission")
def test_the_event_console_actions_are_reachable_without_the_general_permission(
    clients: ClientRegistry,
) -> None:
    """The executables gate comes on top of mkeventd.config, not on top of wato.global."""
    assert clients.GlobalSetting.get(EXECUTABLES_VAR).json["value"] == []


def _read_only(*rw_users: UserId) -> ReadOnlySpec:
    return {"enabled": True, "rw_users": rw_users, "message": "Maintenance in progress"}


def test_a_read_only_setup_refuses_a_write(clients: ClientRegistry, set_config: SetConfig) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)

    with set_config(wato_read_only=_read_only()):
        clients.GlobalSetting.update(INT_VAR, 7, expect_ok=False).assert_status_code(403)
        clients.GlobalSetting.delete(INT_VAR, expect_ok=False).assert_status_code(403)

    assert clients.GlobalSetting.get(INT_VAR).json["value"] == 42


def test_a_read_only_setup_refuses_a_site_write(
    clients: ClientRegistry, set_config: SetConfig, remote_site: str
) -> None:
    clients.GlobalSetting.update_site(remote_site, INT_VAR, 7)

    with set_config(wato_read_only=_read_only()):
        clients.GlobalSetting.update_site(
            remote_site, INT_VAR, 8, expect_ok=False
        ).assert_status_code(403)
        clients.GlobalSetting.delete_site(remote_site, INT_VAR, expect_ok=False).assert_status_code(
            403
        )

    assert clients.GlobalSetting.get_site(remote_site, INT_VAR).json["value"] == 7


def test_a_read_only_setup_still_serves_a_read(
    clients: ClientRegistry, set_config: SetConfig
) -> None:
    with set_config(wato_read_only=_read_only()):
        assert clients.GlobalSetting.get(INT_VAR).json["value"] == INT_DEFAULT


def test_a_user_allowed_to_override_read_only_still_writes(
    clients: ClientRegistry, set_config: SetConfig, with_automation_user: tuple[UserId, str]
) -> None:
    with set_config(wato_read_only=_read_only(with_automation_user[0])):
        assert clients.GlobalSetting.update(INT_VAR, 42).json["value"] == 42


def test_a_disabled_setup_refuses_the_central_scope(
    clients: ClientRegistry, set_config: SetConfig
) -> None:
    with set_config(wato_enabled=False):
        clients.GlobalSetting.get(INT_VAR, expect_ok=False).assert_status_code(403)
        clients.GlobalSetting.update(INT_VAR, 42, expect_ok=False).assert_status_code(403)
        clients.GlobalSetting.delete(INT_VAR, expect_ok=False).assert_status_code(403)


def test_a_disabled_setup_refuses_the_site_scope(
    clients: ClientRegistry, set_config: SetConfig, remote_site: str
) -> None:
    with set_config(wato_enabled=False):
        clients.GlobalSetting.get_site(remote_site, INT_VAR, expect_ok=False).assert_status_code(
            403
        )
        clients.GlobalSetting.update_site(
            remote_site, INT_VAR, 42, expect_ok=False
        ).assert_status_code(403)
        clients.GlobalSetting.delete_site(remote_site, INT_VAR, expect_ok=False).assert_status_code(
            403
        )


def test_the_site_of_a_customer_refuses_the_central_scope(
    clients: ClientRegistry, test_edition: Edition
) -> None:
    with _site_of_a_customer(test_edition):
        clients.GlobalSetting.get(INT_VAR, expect_ok=False).assert_status_code(403)
        clients.GlobalSetting.update(INT_VAR, 42, expect_ok=False).assert_status_code(403)
        clients.GlobalSetting.delete(INT_VAR, expect_ok=False).assert_status_code(403)


def test_the_site_of_a_customer_refuses_the_site_scope(
    clients: ClientRegistry, remote_site: str, test_edition: Edition
) -> None:
    with _site_of_a_customer(test_edition):
        clients.GlobalSetting.get_site(remote_site, INT_VAR, expect_ok=False).assert_status_code(
            403
        )
        clients.GlobalSetting.update_site(
            remote_site, INT_VAR, 42, expect_ok=False
        ).assert_status_code(403)
        clients.GlobalSetting.delete_site(remote_site, INT_VAR, expect_ok=False).assert_status_code(
            403
        )


def test_site_value_falls_back_to_the_central_value(
    clients: ClientRegistry, remote_site: str
) -> None:
    assert clients.GlobalSetting.get_site(remote_site, INT_VAR).json == {
        "site_id": remote_site,
        "varname": INT_VAR,
        "value": INT_DEFAULT,
        "origin": "factory",
    }

    clients.GlobalSetting.update(INT_VAR, 42)
    resp = clients.GlobalSetting.get_site(remote_site, INT_VAR)
    assert resp.json["value"] == 42
    assert resp.json["origin"] == "global"


def test_site_override_replaces_the_central_value(
    clients: ClientRegistry, remote_site: str
) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)
    assert clients.GlobalSetting.update_site(remote_site, INT_VAR, 7).json == {
        "site_id": remote_site,
        "varname": INT_VAR,
        "value": 7,
        "origin": "site",
    }
    # the central value is untouched
    assert clients.GlobalSetting.get(INT_VAR).json["value"] == 42


def test_deleting_a_site_override_falls_back_to_the_central_value(
    clients: ClientRegistry, remote_site: str
) -> None:
    clients.GlobalSetting.update(INT_VAR, 42)
    clients.GlobalSetting.update_site(remote_site, INT_VAR, 7)
    clients.GlobalSetting.delete_site(remote_site, INT_VAR).assert_status_code(204)
    resp = clients.GlobalSetting.get_site(remote_site, INT_VAR)
    assert resp.json["value"] == 42
    assert resp.json["origin"] == "global"


def test_site_scope_changes_are_scoped_to_that_site(
    clients: ClientRegistry, remote_site: str
) -> None:
    clients.GlobalSetting.update_site(remote_site, INT_VAR, 7)
    assert _changes_of(remote_site) == [
        f"Changed site-specific configuration variable {INT_VAR} for site {remote_site}."
    ]
    assert _changes_of(LOCAL_SITE) == []


def test_site_scope_etags(clients: ClientRegistry, remote_site: str) -> None:
    clients.GlobalSetting.update_site(
        remote_site, INT_VAR, 7, etag=None, expect_ok=False
    ).assert_status_code(428)
    clients.GlobalSetting.update_site(
        remote_site, INT_VAR, 7, etag="invalid_etag", expect_ok=False
    ).assert_status_code(412)
    clients.GlobalSetting.update_site(
        remote_site, INT_VAR, 7, etag="valid_etag"
    ).assert_status_code(200)
    clients.GlobalSetting.delete_site(remote_site, INT_VAR, etag="valid_etag").assert_status_code(
        204
    )


def test_the_site_etag_returned_by_an_update_is_still_valid(
    clients: ClientRegistry, remote_site: str
) -> None:
    """Same as for the central scope: the update does not read the value back."""
    etag = clients.GlobalSetting.update_site(remote_site, INT_VAR, 7).headers["ETag"]
    assert clients.GlobalSetting.get_site(remote_site, INT_VAR).headers["ETag"] == etag
    clients.GlobalSetting.request(
        "put",
        url=f"/objects/site_connection/{remote_site}/global_setting/{INT_VAR}",
        body={"value": 8},
        headers={"If-Match": etag},
    ).assert_status_code(200)


def test_site_scope_is_unavailable_without_a_distributed_setup(clients: ClientRegistry) -> None:
    """site_globals_editable() only accepts a site that already carries overrides, and here
    nothing can create the first one. The GUI refuses the same sites."""
    clients.GlobalSetting.get_site(LOCAL_SITE, INT_VAR, expect_ok=False).assert_status_code(404)
    clients.GlobalSetting.update_site(LOCAL_SITE, INT_VAR, 7, expect_ok=False).assert_status_code(
        404
    )
    clients.GlobalSetting.delete_site(LOCAL_SITE, INT_VAR, expect_ok=False).assert_status_code(404)


@pytest.mark.usefixtures("remote_site")
def test_unknown_site_404(clients: ClientRegistry) -> None:
    clients.GlobalSetting.get_site("no_such_site", INT_VAR, expect_ok=False).assert_status_code(404)


def test_the_event_console_is_served_by_the_central_endpoints(
    clients: ClientRegistry, event_console_var: str
) -> None:
    assert clients.GlobalSetting.get(event_console_var).json["value"] is False
    assert clients.GlobalSetting.update(event_console_var, True).json["value"] is True


def test_an_event_console_change_reaches_the_event_console_sites_only(
    clients: ClientRegistry, site_without_event_console: str, event_console_var: str
) -> None:
    clients.GlobalSetting.update(event_console_var, True)
    clients.GlobalSetting.update(INT_VAR, 42)

    assert _changes_of(LOCAL_SITE) == [
        f"Changed global configuration variable {event_console_var}.",
        f"Changed global configuration variable {INT_VAR}.",
    ]
    assert _changes_of(site_without_event_console) == [
        f"Changed global configuration variable {INT_VAR}."
    ]


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


def test_a_remote_site_cannot_enable_the_piggyback_hub_the_central_site_has_disabled(
    clients: ClientRegistry, remote_site: str, piggyback_hub_var: str
) -> None:
    clients.GlobalSetting.update_site(
        remote_site, piggyback_hub_var, True, expect_ok=False
    ).assert_status_code(400)


def test_the_central_site_cannot_disable_the_piggyback_hub_a_remote_site_runs(
    clients: ClientRegistry, remote_site: str, piggyback_hub_var: str
) -> None:
    clients.GlobalSetting.update(piggyback_hub_var, True)
    clients.GlobalSetting.update_site(remote_site, piggyback_hub_var, True)

    clients.GlobalSetting.update(piggyback_hub_var, False, expect_ok=False).assert_status_code(400)


def test_the_central_site_cannot_reset_the_piggyback_hub_a_remote_site_runs(
    clients: ClientRegistry, remote_site: str, piggyback_hub_var: str
) -> None:
    clients.GlobalSetting.update(piggyback_hub_var, True)
    clients.GlobalSetting.update_site(remote_site, piggyback_hub_var, True)

    clients.GlobalSetting.delete(piggyback_hub_var, expect_ok=False).assert_status_code(400)


def _self_signed_ca_pem() -> str:
    return (
        CertificateWithPrivateKey.generate_self_signed(
            common_name="test CA", organization="test", key_size=2048
        )
        .certificate.dump_pem()
        .str
    )


def _trusted_cas_value(*pems: str) -> dict[str, object]:
    return {"use_system_wide_cas": False, "trusted_cas": list(pems)}


def _trust_changes(caplog: pytest.LogCaptureFixture) -> list[str]:
    """The certificate events on the security log."""
    return [
        json.loads(record.getMessage())["summary"]
        for record in caplog.records
        if record.name.startswith("cmk_security")
    ]


def test_adding_a_trusted_ca_is_logged_as_a_security_event(
    clients: ClientRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="cmk_security"):
        clients.GlobalSetting.update(
            "trusted_certificate_authorities", _trusted_cas_value(_self_signed_ca_pem())
        )

    assert _trust_changes(caplog) == ["certificate added"]


@pytest.mark.usefixtures("remote_site")
def test_a_central_trusted_ca_is_logged_once_for_all_the_sites_inheriting_it(
    clients: ClientRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="cmk_security"):
        clients.GlobalSetting.update(
            "trusted_certificate_authorities", _trusted_cas_value(_self_signed_ca_pem())
        )

    assert _trust_changes(caplog) == ["certificate added"]


def test_a_remote_site_override_of_the_trusted_cas_is_logged(
    clients: ClientRegistry, remote_site: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="cmk_security"):
        clients.GlobalSetting.update_site(
            remote_site,
            "trusted_certificate_authorities",
            _trusted_cas_value(_self_signed_ca_pem()),
        )

    assert _trust_changes(caplog) == ["certificate added"]


def test_a_change_of_another_setting_logs_no_certificate_event(
    clients: ClientRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    clients.GlobalSetting.update(
        "trusted_certificate_authorities", _trusted_cas_value(_self_signed_ca_pem())
    )

    with caplog.at_level(logging.INFO, logger="cmk_security"):
        clients.GlobalSetting.update(INT_VAR, 7)

    assert _trust_changes(caplog) == []
