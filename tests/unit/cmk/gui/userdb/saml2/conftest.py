#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest


@pytest.fixture(autouse=True)
def xmlsec1_binary_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock that the xmlsec1 binary exists and is in PATH
    monkeypatch.setattr("saml2.sigver.get_xmlsec_binary", lambda p: "xmlsec1")
    monkeypatch.setattr("os.path.exists", lambda p: True)


@pytest.fixture(name="raw_config")
def fixture_raw_config() -> dict[str, Any]:
    return {
        "type": "saml2",
        "version": "1.0.0",
        "id": "uuid123",
        "description": "",
        "comment": "",
        "docu_url": "",
        "disabled": False,
        "interface_config": {
            "connection_timeout": (12, 12),
            "checkmk_server_url": "https://myhost.com",
            "idp_metadata_endpoint": "https://myidp.com/some/path/to/metadata.php",
            "user_id_attribute": "username",
        },
    }


@pytest.fixture
def metadata_from_idp(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata_str = """<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" xmlns:ds="https://www.w3.org/2000/09/xmldsig#" entityID="https://myidp.com/some/path/to/metadata.php">
  <md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="https://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>ABC</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:KeyDescriptor use="encryption">
      <ds:KeyInfo xmlns:ds="https://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>ABC</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="https://myidp.com/some/path/to//SingleLogoutService.php"/>
    <md:NameIDFormat>urn:oasis:names:tc:SAML:2.0:nameid-format:transient</md:NameIDFormat>
    <md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="https://myidp.com/some/path/to//SSOService.php"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>

"""
    monkeypatch.setattr(
        "cmk.gui.userdb.saml2.interface._metadata_from_idp", lambda c, t: metadata_str
    )
