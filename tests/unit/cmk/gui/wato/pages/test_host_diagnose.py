#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Regression tests for the legacy 'Test connection to host' AJAX handler.

The SNMPv3 credentials typed into the form were being ignored because the
frontend forwarded only the hidden '_orig' field of the Password valuespec.
After the fix, the AJAX handler parses the submitted form via the valuespecs
themselves, so Password.from_html_vars() correctly prefers the typed value
over the stored, encrypted _orig.
"""

import base64
import hashlib

import pytest
from bs4 import BeautifulSoup, Tag

from cmk.utils.hostaddress import HostName

from cmk.gui.http import request
from cmk.gui.utils.encrypter import Encrypter
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.theme import Theme
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.wato.pages.host_diagnose import _vs_host, _vs_rules


def _auth_no_priv_vars(
    *,
    typed_password: str,
    orig_password: str | None,
    auth_proto: str = "md5",
    security_name: str = "user1",
) -> dict[str, str]:
    """Build request vars for an SNMPv3 authNoPriv credential submission.

    Mirrors what the refactored host_diagnose.ts forwards: both the visible
    password input (_1_3) and, when present, the hidden _orig companion
    (_1_3_orig) rendered by Password.render_input().
    """
    vars_: dict[str, str] = {
        "vs_host_p_snmp_v3_credentials_USE": "on",
        "vs_host_p_snmp_v3_credentials_use": "1",
        "vs_host_p_snmp_v3_credentials_1_1": DropdownChoice.option_id(auth_proto),
        "vs_host_p_snmp_v3_credentials_1_2": security_name,
        "vs_host_p_snmp_v3_credentials_1_3": typed_password,
    }
    if orig_password is not None:
        vars_["vs_host_p_snmp_v3_credentials_1_3_orig"] = orig_password
    return vars_


def _set_vars(vars_: dict[str, str]) -> None:
    for key, value in vars_.items():
        request.set_var(key, value)


@pytest.mark.skipif(
    not hasattr(hashlib, "scrypt"), reason="OpenSSL version too old, must be >= 1.1"
)
def test_vs_host_prefers_typed_snmpv3_password_over_orig(request_context: None) -> None:
    """Typed password must win over the stored _orig."""
    stored_encrypted = base64.b64encode(Encrypter.encrypt("stored-pw")).decode("ascii")
    _set_vars(_auth_no_priv_vars(typed_password="typed-pw", orig_password=stored_encrypted))

    result = _vs_host(HostName("host1")).from_html_vars("vs_host")

    assert result["snmp_v3_credentials"] == ("authNoPriv", "md5", "user1", "typed-pw")


@pytest.mark.skipif(
    not hasattr(hashlib, "scrypt"), reason="OpenSSL version too old, must be >= 1.1"
)
def test_vs_host_decrypts_snmpv3_orig_when_typed_is_empty(request_context: None) -> None:
    """When the user does not re-enter the password, the stored _orig is used."""
    stored_encrypted = base64.b64encode(Encrypter.encrypt("stored-pw")).decode("ascii")
    _set_vars(_auth_no_priv_vars(typed_password="", orig_password=stored_encrypted))

    result = _vs_host(HostName("host1")).from_html_vars("vs_host")

    assert result["snmp_v3_credentials"] == ("authNoPriv", "md5", "user1", "stored-pw")


def test_vs_host_returns_empty_password_when_no_typed_and_no_orig(
    request_context: None,
) -> None:
    """No typed password and no _orig must not raise a decrypt error.

    This reproduces the scenario where all tests failed with
    'API Error: Decryption of SNMPv3 password failed.'.
    """
    _set_vars(_auth_no_priv_vars(typed_password="", orig_password=None))

    result = _vs_host(HostName("host1")).from_html_vars("vs_host")

    assert result["snmp_v3_credentials"] == ("authNoPriv", "md5", "user1", "")


def test_vs_host_parses_snmpv1_community(request_context: None) -> None:
    _set_vars(
        {
            "vs_host_p_snmp_community_USE": "on",
            "vs_host_p_snmp_community": "plain-community",
        }
    )

    result = _vs_host(HostName("host1")).from_html_vars("vs_host")

    assert result["snmp_community"] == "plain-community"


def _auth_priv_vars(
    *,
    typed_auth_pw: str,
    typed_priv_pw: str,
    auth_proto: str = "md5",
    priv_proto: str = "DES",
    security_name: str = "user1",
) -> dict[str, str]:
    """Build request vars for an SNMPv3 authPriv credential submission."""
    return {
        "vs_host_p_snmp_v3_credentials_USE": "on",
        "vs_host_p_snmp_v3_credentials_use": "2",
        "vs_host_p_snmp_v3_credentials_2_1": DropdownChoice.option_id(auth_proto),
        "vs_host_p_snmp_v3_credentials_2_2": security_name,
        "vs_host_p_snmp_v3_credentials_2_3": typed_auth_pw,
        "vs_host_p_snmp_v3_credentials_2_4": DropdownChoice.option_id(priv_proto),
        "vs_host_p_snmp_v3_credentials_2_5": typed_priv_pw,
    }


def test_vs_host_parses_snmpv3_auth_priv_credentials(request_context: None) -> None:
    """authPriv: parse all 6 tuple fields (covers the 6-tuple match arm)."""
    _set_vars(_auth_priv_vars(typed_auth_pw="auth-pw", typed_priv_pw="priv-pw"))

    result = _vs_host(HostName("host1")).from_html_vars("vs_host")

    assert result["snmp_v3_credentials"] == (
        "authPriv",
        "md5",
        "user1",
        "auth-pw",
        "DES",
        "priv-pw",
    )


def test_vs_rules_parses_rule_vars(request_context: None) -> None:
    _set_vars(
        {
            "vs_rules_p_agent_port": "6557",
            "vs_rules_p_tcp_connect_timeout": "7.0",
            "vs_rules_p_snmp_timeout": "3",
            "vs_rules_p_snmp_retries": "2",
        }
    )

    result = _vs_rules().from_html_vars("vs_rules")

    assert result == {
        "agent_port": 6557,
        "tcp_connect_timeout": 7.0,
        "snmp_timeout": 3,
        "snmp_retries": 2,
    }


# ---------------------------------------------------------------------------
# Render-side coverage: prove that the HTML the form actually emits matches
# the field naming that host_diagnose.ts forwards and the from_html_vars
# tests above assume. Together these close the render -> POST -> parse
# round-trip on the Python side.
# ---------------------------------------------------------------------------


def _render_vs_host(value: dict[str, object]) -> BeautifulSoup:
    # render_input() emits help icons; the bazel unit-test sandbox has no icons
    # linked, so the theme's detect_icon_path would raise. Stub it for the
    # duration of the render the tests only care about form field names.
    with pytest.MonkeyPatch.context() as mp, output_funnel.plugged():
        mp.setattr(Theme, "detect_icon_path", lambda self, *a, **kw: "")
        _vs_host(HostName("host1")).render_input("vs_host", value)
        return BeautifulSoup(output_funnel.drain(), "html.parser")


def _input_by_name(soup: BeautifulSoup, name: str) -> dict[str, str]:
    el = soup.find(attrs={"name": name})
    assert isinstance(el, Tag), f"missing form element with name={name!r}"
    return {k: str(v) for k, v in el.attrs.items()}


@pytest.mark.skipif(
    not hasattr(hashlib, "scrypt"), reason="OpenSSL version too old, must be >= 1.1"
)
def test_render_emits_snmpv3_password_with_visible_and_orig_inputs(
    request_context: None,
) -> None:
    """The rendered form must emit BOTH the visible password input and the
    hidden _orig companion -- otherwise host_diagnose.ts cannot forward them
    and Password.from_html_vars cannot fall back to the stored value.
    """
    soup = _render_vs_host(
        {
            "hostname": HostName("host1"),
            "snmp_v3_credentials": ("authNoPriv", "md5", "user1", "stored-pw"),
        }
    )

    visible = _input_by_name(soup, "vs_host_p_snmp_v3_credentials_1_3")
    assert visible["type"] == "password"

    orig = _input_by_name(soup, "vs_host_p_snmp_v3_credentials_1_3_orig")
    assert orig["type"] == "hidden"
    # _orig holds the encrypted stored password; round-trip via Encrypter.
    assert Encrypter.decrypt(base64.b64decode(orig["value"].encode("ascii"))) == "stored-pw"


def test_render_emits_field_names_with_vs_host_prefix(request_context: None) -> None:
    """host_diagnose.ts filters form fields by the 'vs_host_' / 'vs_rules_'
    prefix. Verify the renderer emits the prefix our filter expects.
    """
    soup = _render_vs_host(
        {
            "hostname": HostName("host1"),
            "snmp_v3_credentials": ("noAuthNoPriv", "user1"),
        }
    )

    # USE checkbox for the snmp_v3_credentials Dictionary entry.
    assert _input_by_name(soup, "vs_host_p_snmp_v3_credentials_USE")
    # Alternative selector (which sub-form is active).
    assert _input_by_name(soup, "vs_host_p_snmp_v3_credentials_use")
    # Security name from the noAuthNoPriv tuple (index 1).
    assert _input_by_name(soup, "vs_host_p_snmp_v3_credentials_0_1")
