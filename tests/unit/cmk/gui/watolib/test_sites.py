#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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

from typing import Any, cast

import pytest

from cmk.ccc.site import omd_site, SiteId
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.user_connection_config_types import LDAPUserConnectionConfig
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
from tests.testlib.gui.web_test_app import SetConfig


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


def test_auth_connections_round_trip_multi_entry_and_reassignment() -> None:
    """Multi-entry (SAML+LDAP) lists and the emptied list left by a reassignment round-trip disk → form → disk unchanged."""
    multi_entry = [
        ("ldap", "ldap_a"),
        ("ldap", "ldap_b"),
        ("saml", {"connection_id": "saml_a"}),
        ("saml", {"connection_id": "saml_b"}),
    ]
    assert _auth_connections_from_disk(multi_entry) == ("list", multi_entry)
    assert _auth_connections_to_disk(("list", multi_entry)) == multi_entry

    reassigned = [("saml", {"connection_id": "saml_a"})]
    assert _auth_connections_to_disk(_auth_connections_from_disk(reassigned)) == reassigned
    # An emptied list is a real value ("no connections"), not a fallback to another shape.
    assert _auth_connections_to_disk(_auth_connections_from_disk([])) == []


def test_auth_connections_unmodified_save_writes_identical_shape() -> None:
    """An unmodified save round-trips every on-disk shape exactly (no ``sites.mk`` diff)."""
    entries = [("ldap", "ldap_a"), ("saml", {"connection_id": "saml_a"})]
    assert _auth_connections_to_disk(_auth_connections_from_disk(entries)) == entries
    assert _auth_connections_to_disk(_auth_connections_from_disk("disabled")) == "disabled"
    all_types = ("all", ["saml", "ldap"])
    assert _auth_connections_to_disk(_auth_connections_from_disk(all_types)) == all_types


def test_user_attribute_sync_unmodified_save_writes_identical_shape() -> None:
    """Same no-diff guarantee for the second field across all three on-disk shapes (``all`` / explicit list / ``disabled``)."""
    assert _user_attribute_sync_to_disk(_user_attribute_sync_from_disk("all")) == "all"
    explicit = ["ldap_a", "ldap_b"]
    assert _user_attribute_sync_to_disk(_user_attribute_sync_from_disk(explicit)) == explicit
    assert _user_attribute_sync_to_disk(_user_attribute_sync_from_disk("disabled")) == "disabled"


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


def _ldap_connection(connection_id: str) -> LDAPUserConnectionConfig:
    return cast(
        LDAPUserConnectionConfig,
        {"type": "ldap", "id": connection_id, "name": connection_id, "disabled": False},
    )


def test_user_attribute_sync_form_spec_accepts_dash_in_connection_id(
    set_config: SetConfig,
    request_context: None,
) -> None:
    """A dashed LDAP connection id can be offered for attribute sync.

    Element names in the public form-spec API must be Python identifiers, so
    building this selector from a dashed id used to raise ``ValueError`` and the
    whole site-configuration page failed to render — while the connection form's
    own id rule ("letters, digits, dash and underscore") hands such ids out. A
    dynamically built choice list therefore has to use the extended element type,
    which does not impose the identifier rule.

    Site ids are a separate space with its own remedy: werk 18761 restricts a new
    one to what ``omd create`` accepts, so it cannot carry a dash. Connection ids
    keep the looser rule, which is why this selector still has to tolerate one.
    """
    with set_config(user_connections=[_ldap_connection("ldap-with-dash")]):
        form_spec = SiteManagement.user_attribute_sync_connections_form_spec()

    assert isinstance(form_spec, TransformDataForLegacyFormatOrRecomposeFunction)
    inner = form_spec.wrapped_form_spec
    assert hasattr(inner, "elements")
    explicit_list = next(element for element in inner.elements if element.name == "list")
    offered_connection_ids = [choice.name for choice in explicit_list.parameter_form.elements]

    assert "ldap-with-dash" in offered_connection_ids, (
        "The dashed LDAP connection id is not offered for attribute sync, so a "
        "connection the creation form accepts cannot be selected here."
    )


def _editable_connection_elements(*, saml_supported: bool) -> list[Any]:
    """Return the per-entry connection choices of the nested ``"list"`` widget
    built from stubbed connection choices."""
    template = SiteManagement._editable_connections_form_spec(
        ldap_choices=[("ldap_a", "LDAP A")],
        saml_choices=[("saml_a", "SAML A")] if saml_supported else None,
    ).element_template
    assert hasattr(template, "elements")
    return list(template.elements)


def test_editable_connections_form_spec_offers_ldap_and_saml_when_supported() -> None:
    """The nested "list" connection widget renders an LDAP pick and, when distributed
    SAML is supported, a SAML pick whose sub-form carries the connection_id,
    metadata_endpoint and acs_endpoint fields."""
    elements = _editable_connection_elements(saml_supported=True)
    assert [element.name for element in elements] == ["ldap", "saml"]
    assert [choice.name for choice in elements[0].parameter_form.elements] == ["ldap_a"]
    saml_subform = elements[1].parameter_form
    assert set(saml_subform.elements) == {"connection_id", "metadata_endpoint", "acs_endpoint"}
    assert [
        choice.name for choice in saml_subform.elements["connection_id"].parameter_form.elements
    ] == ["saml_a"]


def test_connection_pick_accepts_dash_in_connection_id() -> None:
    """A connection id containing a dash can be offered as a per-site pick.

    The product's own id rule (the ``ID`` valuespec behind the connection's "ID"
    field) accepts "letters, digits, dash and underscore", so a dashed id is a
    legal connection id and reaches this selector. Form-spec *element names* are
    otherwise required to be Python identifiers, which a dash is not — so
    building the pick must not choke on an id the creation form let through.
    """
    template = SiteManagement._editable_connections_form_spec(
        ldap_choices=[("ldap-with-dash", "LDAP dashed")],
        saml_choices=[("saml-with-dash", "SAML dashed")],
    ).element_template
    assert hasattr(template, "elements")
    elements = list(template.elements)

    assert [choice.name for choice in elements[0].parameter_form.elements] == ["ldap-with-dash"], (
        "The dashed LDAP connection id is not offered as a per-site pick, so a "
        "connection the creation form accepts cannot be assigned to a site."
    )
    saml_subform = elements[1].parameter_form
    assert [
        choice.name for choice in saml_subform.elements["connection_id"].parameter_form.elements
    ] == ["saml-with-dash"]


def test_auth_connections_round_trip_dashed_connection_id() -> None:
    """A dashed connection id survives the disk → form → disk round trip, so a
    site assignment referencing it is not silently dropped or mangled."""
    entries = [("ldap", "ldap-with-dash"), ("saml", {"connection_id": "saml-with-dash"})]
    assert _auth_connections_from_disk(entries) == ("list", entries)
    assert _auth_connections_to_disk(("list", entries)) == entries


def test_editable_connections_form_spec_omits_saml_when_not_supported() -> None:
    """Without distributed SAML support the nested "list" widget offers only the LDAP pick."""
    elements = _editable_connection_elements(saml_supported=False)
    assert [element.name for element in elements] == ["ldap"]


def test_editable_connections_form_spec_rejects_empty_list(request_context: None) -> None:
    """Choosing "Use the following" requires at least one connection entry —
    an empty list would be semantically "disabled" behind a misleading label."""
    visitor = get_visitor(
        SiteManagement._editable_connections_form_spec(
            ldap_choices=[("ldap_a", "LDAP A")], saml_choices=None
        ),
        VisitorOptions(migrate_values=False, mask_values=False),
    )

    validation_messages = visitor.validate(RawDiskData([]))
    assert [message.message for message in validation_messages] == [
        "Please add at least one connection or choose a different option."
    ]

    assert visitor.validate(RawDiskData([("ldap", "ldap_a")])) == []


@pytest.mark.parametrize(
    "site_id",
    [
        pytest.param("remote-1", id="dash"),
        pytest.param("1remote", id="leading_digit"),
        pytest.param("a" * 17, id="too_long"),
        pytest.param("sitä", id="non_ascii"),
        pytest.param("remote\n", id="trailing_newline"),
        pytest.param("", id="empty"),
    ],
)
def test_validate_configuration_rejects_invalid_new_site_id(site_id: str) -> None:
    with pytest.raises(MKUserError, match="site id"):
        SiteManagement.validate_configuration(
            SiteId(site_id),
            _remote_site_config(),
            SiteConfigurations({SiteId("central"): _local_site_config()}),
        )


@pytest.mark.parametrize(
    "site_id",
    [
        pytest.param("remote", id="letters"),
        pytest.param("remote_1", id="digits_and_underscore"),
        pytest.param("_r", id="leading_underscore"),
        pytest.param("a" * 16, id="maximum_length"),
    ],
)
def test_validate_configuration_accepts_valid_new_site_id(site_id: str) -> None:
    SiteManagement.validate_configuration(
        SiteId(site_id),
        _remote_site_config(),
        SiteConfigurations({SiteId("central"): _local_site_config()}),
    )


def test_validate_configuration_accepts_invalid_site_id_of_existing_connection() -> None:
    site_id = SiteId("remote-1")
    SiteManagement.validate_configuration(
        site_id,
        _remote_site_config(),
        SiteConfigurations(
            {SiteId("central"): _local_site_config(), site_id: _remote_site_config()}
        ),
    )
