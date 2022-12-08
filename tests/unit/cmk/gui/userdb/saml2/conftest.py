#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest
from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.config import SPConfig


@pytest.fixture(autouse=True)
def xmlsec1_binary_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock that the xmlsec1 binary exists and is in PATH
    monkeypatch.setattr("saml2.sigver.get_xmlsec_binary", lambda p: "xmlsec1")
    monkeypatch.setattr("os.path.exists", lambda p: True)


@pytest.fixture(name="raw_config")
def fixture_raw_config() -> dict[str, Any]:
    idp_metadata = {
        "inline": [
            """<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" entityID="http://myidp.com/some/path/to/metadata.php">
  <md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>ABC</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:KeyDescriptor use="encryption">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>ABC</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="http://myidp.com/some/path/to//SingleLogoutService.php"/>
    <md:NameIDFormat>urn:oasis:names:tc:SAML:2.0:nameid-format:transient</md:NameIDFormat>
    <md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="http://myidp.com/some/path/to//SSOService.php"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>

"""
        ],
    }

    sp_configuration = {
        "endpoints": {
            "assertion_consumer_service": [
                (
                    "http://myhost/mysite/check_mk/saml_acs.py?acs",
                    BINDING_HTTP_REDIRECT,
                ),
                ("http://myhost/mysite/check_mk/saml_acs.py?acs", BINDING_HTTP_POST),
            ],
        },
        "allow_unsolicited": True,
        "authn_requests_signed": False,
        "logout_requests_signed": False,
        "want_assertions_signed": False,
        "want_response_signed": False,
    }

    settings = {
        "entityid": "http://myhost/mysite/check_mk/saml_metadata.py",
        "metadata": idp_metadata,
        "service": {
            "sp": sp_configuration,
        },
        "allow_unknown_attributes": True,
    }
    return settings


@pytest.fixture()
def config(raw_config: dict[str, Any]) -> SPConfig:
    cfg = SPConfig()
    cfg.load(raw_config)
    return cfg


@pytest.fixture
def metadata() -> str:
    return " ".join(
        """<ns0:EntityDescriptor xmlns:ns0="urn:oasis:names:tc:SAML:2.0:metadata" entityID="http://myhost/mysite/check_mk/saml_metadata.py">
   <ns0:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol" AuthnRequestsSigned="false" WantAssertionsSigned="false">
      <ns0:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="http://myhost/mysite/check_mk/saml_acs.py?acs" index="1" />
      <ns0:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="http://myhost/mysite/check_mk/saml_acs.py?acs" index="2" />
   </ns0:SPSSODescriptor>
</ns0:EntityDescriptor>""".split()
    ).replace("> <", "><")
