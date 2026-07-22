#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the ``authentication_connections`` and
``user_attribute_sync_connections`` form-spec chains in
``cmk.gui.watolib.sites``.

Each chain has independently testable parts:

* ``_auth_connections_from_disk`` / ``_auth_connections_to_disk`` and
  ``_user_attribute_sync_from_disk`` / ``_user_attribute_sync_to_disk`` —
  pure functions that bridge the on-disk representation and the form
  spec's cascading-choice tuple form.
* ``SiteManagement.authentication_connections_form_spec`` /
  ``SiteManagement.user_attribute_sync_connections_form_spec`` — offer the
  same top-level choices for every site; there is no "inherit from the
  central site" option.
"""

import pytest

from cmk.ccc.site import omd_site, SiteId
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.watolib.sites import (
    _auth_connections_from_disk,
    _auth_connections_to_disk,
    _user_attribute_sync_from_disk,
    _user_attribute_sync_to_disk,
    SiteManagement,
)
from cmk.livestatus_client import (
    NetworkSocketDetails,
    SAMLAuthenticationEntry,
    SiteConfiguration,
    SiteConfigurations,
)


def _local_site_config() -> SiteConfiguration:
    """A site config whose socket marks it as the central site."""
    return SiteConfiguration(
        id=SiteId("central"),
        alias="Central",
        socket=("local", None),
        disable_wato=False,
        disabled=False,
        insecure=False,
        url_prefix="/central/",
        multisiteurl="",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication=None,
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=True,
    )


def _remote_site_config() -> SiteConfiguration:
    """A site config whose socket marks it as a remote site."""
    return SiteConfiguration(
        id=SiteId("remote"),
        alias="Remote",
        socket=(
            "tcp",
            NetworkSocketDetails(
                address=("127.0.0.1", 6557),
                tls=("encrypted", {"verify": True}),
            ),
        ),
        disable_wato=True,
        disabled=False,
        insecure=False,
        url_prefix="/remote/",
        multisiteurl="http://remote/check_mk/",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave",
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )


def test_auth_connections_from_disk_wraps_bare_list() -> None:
    entries = [("ldap", "ldap_a"), ("saml", {"connection_id": "saml_a"})]
    assert _auth_connections_from_disk(entries) == ("list", entries)


def test_auth_connections_from_disk_translates_disabled() -> None:
    assert _auth_connections_from_disk("disabled") == ("disabled", True)


def test_auth_connections_from_disk_passes_tuple_form_through() -> None:
    """The site-edit page pre-wraps the value so the form-friendly tuple
    arrives here directly; pass it through unchanged. The on-disk
    ``("all", [types])`` form already matches the form tuple."""
    all_form = ("all", ["ldap"])
    assert _auth_connections_from_disk(all_form) == all_form
    list_form = ("list", [("ldap", "ldap_a")])
    assert _auth_connections_from_disk(list_form) == list_form


def test_auth_connections_to_disk_unwraps_list_choice() -> None:
    entries = [("ldap", "ldap_a")]
    assert _auth_connections_to_disk(("list", entries)) == entries


def test_auth_connections_to_disk_keeps_all_choice_tuple() -> None:
    assert _auth_connections_to_disk(("all", ["saml", "ldap"])) == ("all", ["saml", "ldap"])


def test_auth_connections_to_disk_unwraps_disabled_choice() -> None:
    assert _auth_connections_to_disk(("disabled", True)) == "disabled"


def _choice_names(form_spec: object) -> list[str]:
    """Return the top-level ``CascadingSingleChoice`` element names from the
    wrapped form spec returned by ``authentication_connections_form_spec``."""
    assert isinstance(form_spec, TransformDataForLegacyFormatOrRecomposeFunction)
    inner = form_spec.wrapped_form_spec
    assert hasattr(inner, "elements")
    return [element.name for element in inner.elements]


def test_authentication_connections_form_spec_choices(
    request_context: None,
) -> None:
    """The choices are the same for every site — there is no
    "inherit from the central site" option."""
    assert _choice_names(SiteManagement.authentication_connections_form_spec()) == [
        "disabled",
        "list",
        "all",
    ]


def test_saml_endpoint_widgets_carry_pending_placeholder() -> None:
    """A freshly added SAML list row has empty endpoint values (they are only
    computed on save), so both widgets must announce the pending URL via
    their placeholder instead of rendering an empty field."""
    for widget in (
        SiteManagement._saml_metadata_endpoint_widget(),
        SiteManagement._saml_acs_endpoint_widget(),
    ):
        assert widget.placeholder is not None
        assert (
            widget.placeholder.localize(lambda s: s)
            == "The URL will be generated automatically after you save the form."
        )


def _distributed_site_configs(central: SiteConfiguration) -> SiteConfigurations:
    """Central plus one remote without the key and one with its own connections."""
    inheriting_remote = _remote_site_config()
    explicit_remote = _remote_site_config()
    explicit_remote["id"] = SiteId("remote_explicit")
    explicit_remote["authentication_connections"] = [("ldap", "ldap_a")]
    return SiteConfigurations(
        {
            omd_site(): central,
            SiteId("remote"): inheriting_remote,
            SiteId("remote_explicit"): explicit_remote,
        }
    )


def test_get_connected_sites_to_update_central_auth_change_does_not_fan_out() -> None:
    """Every site carries its own ``authentication_connections`` value —
    editing the central site's value no longer affects other sites."""
    current_config = _local_site_config()
    current_config["authentication_connections"] = [
        ("saml", SAMLAuthenticationEntry(connection_id="saml_a"))
    ]
    assert (
        SiteManagement.get_connected_sites_to_update(
            new_or_deleted_connection=False,
            modified_site=omd_site(),
            current_config=current_config,
            old_config=_local_site_config(),
            site_configs=_distributed_site_configs(current_config),
        )
        == set()
    )


def test_get_connected_sites_to_update_unchanged_auth_flags_no_sites() -> None:
    current_config = _local_site_config()
    assert (
        SiteManagement.get_connected_sites_to_update(
            new_or_deleted_connection=False,
            modified_site=omd_site(),
            current_config=current_config,
            old_config=_local_site_config(),
            site_configs=_distributed_site_configs(current_config),
        )
        == set()
    )


def test_get_connected_sites_to_update_remote_auth_change_does_not_fan_out() -> None:
    central = _local_site_config()
    current_config = _remote_site_config()
    current_config["authentication_connections"] = [
        ("saml", SAMLAuthenticationEntry(connection_id="saml_a"))
    ]
    assert (
        SiteManagement.get_connected_sites_to_update(
            new_or_deleted_connection=False,
            modified_site=SiteId("remote"),
            current_config=current_config,
            old_config=_remote_site_config(),
            site_configs=_distributed_site_configs(central),
        )
        == set()
    )


@pytest.mark.parametrize(
    ["disk_value", "form_value"],
    [
        ("disabled", ("disabled", True)),
        ("all", ("all", True)),
        (["ldap_a", "ldap_b"], ("list", ["ldap_a", "ldap_b"])),
    ],
)
def test_user_attribute_sync_from_disk(disk_value: object, form_value: tuple[str, object]) -> None:
    assert _user_attribute_sync_from_disk(disk_value) == form_value


def test_user_attribute_sync_from_disk_passes_tuple_form_through() -> None:
    assert _user_attribute_sync_from_disk(("list", ["ldap_a"])) == ("list", ["ldap_a"])


@pytest.mark.parametrize(
    ["form_value", "disk_value"],
    [
        (("disabled", True), "disabled"),
        (("all", True), "all"),
        (("list", ["ldap_a", "ldap_b"]), ["ldap_a", "ldap_b"]),
    ],
)
def test_user_attribute_sync_to_disk(form_value: tuple[str, object], disk_value: object) -> None:
    assert _user_attribute_sync_to_disk(form_value) == disk_value


def test_user_attribute_sync_form_spec_choices(
    request_context: None,
) -> None:
    """The choices are the same for every site — there is no
    "inherit from the central site" option."""
    assert _choice_names(SiteManagement.user_attribute_sync_connections_form_spec()) == [
        "disabled",
        "all",
        "list",
    ]
