#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the ``authentication_connections`` form-spec chain in
``cmk.gui.watolib.sites``.

The chain has three parts that are independently testable:

* ``_auth_connections_from_disk`` / ``_auth_connections_to_disk`` —
  pure functions that bridge the on-disk representation (a bare
  ``list[AuthenticationConnectionEntry]`` if the per-site override is
  set, or the key being absent for "inherit from central") and the form
  spec's cascading-choice tuple form.
* ``SiteManagement.authentication_connections_form_spec`` — selects the
  available top-level choices based on whether the edited site is the
  central site itself (no ``"central_site"`` self-reference) or a remote
  (both ``"central_site"`` and ``"list"``).
"""

import pytest

from livestatus import (
    NetworkSocketDetails,
    SiteConfiguration,
)

from cmk.ccc.site import SiteId
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.watolib.sites import (
    _auth_connections_from_disk,
    _auth_connections_to_disk,
    DROP_KEY,
    SiteManagement,
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


def test_auth_connections_from_disk_translates_absent_to_central_site_choice() -> None:
    """Absent key (loaded as ``None``) maps to the ``"central_site"`` form
    choice with an empty mapping; the site-edit page injects the real
    read-only connection data at render time."""
    assert _auth_connections_from_disk(None) == ("central_site", {})


def test_auth_connections_from_disk_wraps_bare_list() -> None:
    entries = [("ldap", "ldap_a"), ("saml", {"connection_id": "saml_a"})]
    assert _auth_connections_from_disk(entries) == ("list", entries)


def test_auth_connections_from_disk_passes_tuple_form_through() -> None:
    """The site-edit page pre-wraps the value so the form-friendly tuple
    arrives here directly; pass it through unchanged."""
    central = ("central_site", {"connection_0": {"connection_id": "saml_a"}})
    assert _auth_connections_from_disk(central) == central
    list_form = ("list", [("ldap", "ldap_a")])
    assert _auth_connections_from_disk(list_form) == list_form


def test_auth_connections_to_disk_unwraps_list_choice() -> None:
    entries = [("ldap", "ldap_a")]
    assert _auth_connections_to_disk(("list", entries)) == entries


def test_auth_connections_to_disk_returns_drop_key_for_central_site() -> None:
    assert (
        _auth_connections_to_disk(("central_site", {"connection_0": {"connection_id": "saml_a"}}))
        is DROP_KEY
    )


def _choice_names(form_spec: object) -> list[str]:
    """Return the top-level ``CascadingSingleChoice`` element names from the
    wrapped form spec returned by ``authentication_connections_form_spec``."""
    assert isinstance(form_spec, TransformDataForLegacyFormatOrRecomposeFunction)
    inner = form_spec.wrapped_form_spec
    assert hasattr(inner, "elements")
    return [element.name for element in inner.elements]


def test_authentication_connections_form_spec_local_site_omits_central_site_choice(
    request_context: None,
) -> None:
    """Editing the central site must not offer ``"central_site"`` — it would
    be a self-reference."""
    assert _choice_names(
        SiteManagement.authentication_connections_form_spec(_local_site_config())
    ) == ["list"]


def test_authentication_connections_form_spec_remote_site_offers_both_choices(
    request_context: None,
) -> None:
    """A remote site can either inherit from the central or pick its own list."""
    assert _choice_names(
        SiteManagement.authentication_connections_form_spec(_remote_site_config())
    ) == ["central_site", "list"]


def test_authentication_connections_form_spec_no_site_config_offers_both_choices(
    request_context: None,
) -> None:
    """Without a site configuration (e.g. when adding a new connection), both
    choices are available — the form cannot yet know whether it edits the
    central."""
    assert _choice_names(SiteManagement.authentication_connections_form_spec()) == [
        "central_site",
        "list",
    ]


def test_central_site_connections_readonly_data_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.gui.watolib.sites.central_site_inherited_connections",
        lambda callback_url: [],
    )
    assert SiteManagement.central_site_connections_readonly_data("http://remote/check_mk/") == {
        "_placeholder": "-"
    }


def test_central_site_connections_readonly_data_builds_aligned_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.watolib.sites.central_site_inherited_connections",
        lambda callback_url: [
            ("saml", {"connection_id": "s", "metadata_endpoint": "m", "acs_endpoint": "a"}),
            ("ldap", "l"),
        ],
    )
    assert SiteManagement.central_site_connections_readonly_data("http://remote/check_mk/") == {
        "connection_0": {"connection_id": "s", "metadata_endpoint": "m", "acs_endpoint": "a"},
        "connection_1": {"connection_id": "l"},
    }
