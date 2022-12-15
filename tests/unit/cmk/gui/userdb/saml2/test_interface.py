#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import re
import xml
import zlib
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from saml2.config import SPConfig
from saml2.validate import ResponseLifetimeExceed

from cmk.utils.type_defs import UserId

from cmk.gui.userdb.saml2.interface import Authenticated, Interface

VALID_AUTHENTICATION_REQUEST_PATTERN = re.compile(
    " ".join(
        """<ns0:AuthnRequest xmlns:ns0="urn:oasis:names:tc:SAML:2\\.0:protocol" xmlns:ns1="urn:oasis:names:tc:SAML:2\\.0:assertion" ID="id-[a-zA-Z0-9]{17}" Version="2\\.0" IssueInstant="[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z" Destination="http://myidp\\.com/some/path/to//SSOService\\.php" ProtocolBinding="\\(\'http://myhost/mysite/check_mk/saml_acs\\.py\\?acs\', \'urn:oasis:names:tc:SAML:2\\.0:bindings:HTTP-POST\'\\)">
   <ns1:Issuer Format="urn:oasis:names:tc:SAML:2\\.0:nameid-format:entity">http://myhost/mysite/check_mk/saml_metadata\\.py</ns1:Issuer>
   <ns0:NameIDPolicy Format="urn:oasis:names:tc:SAML:2\\.0:nameid-format:persistent" AllowCreate="false" />
</ns0:AuthnRequest>""".split()
    ).replace("> <", "><")
)


def _encode(string: str) -> str:
    return base64.b64encode(string.encode("utf-8")).decode("utf-8")


def _authentication_request_response(
    response_id: str, timestamp: datetime | None = None, valid_until: datetime | None = None
) -> str:
    timestamp_fmt = "%Y-%m-%dT%H:%M:%SZ"
    now = datetime.utcnow()

    if not timestamp:
        timestamp = now
    if not valid_until:
        valid_until = now + timedelta(days=5)

    return _encode(
        f"""<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                        xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                        ID="_a639dc4ab55961d203419f46689efcc801e950819e"
                        Version="2.0"
                        IssueInstant="{datetime.strftime(timestamp, timestamp_fmt)}"
                        Destination="http://myhost/mysite/check_mk/saml_acs.py?acs"
                        InResponseTo="{response_id}"
                        >
            <saml:Issuer>http://myidp.com/some/path/to/metadata.php</saml:Issuer>
            <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" />
                    <ds:Reference URI="#_a639dc4ab55961d203419f46689efcc801e950819e">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature" />
                            <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
                        <ds:DigestValue>rrgTHuEqDHQOktBTEi5onR8ojtk=</ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue>ErQMB6wSQ6U8PjZeG8GUX+O1GA5lwYN9sWC33+mjbs9i25TWDE1wjsWU2mnI7VZED0h0K8GkTwTItCCpScdJ8dh6g7lo1oXBz4N17l8Gd0RxUEt72MI/2F30Hkri13bZMegmPT2/BsdcgEh7ILRpaCWryyAyokz+TS9uoY+Lc0U88241wkj1r2TIFdtU6WxPlL12MaBOms3C3XJ4/R5d0salpAQ09ytcmMo11cZSIgPcRFQacRoUSDB+yZ04ld5FYaZ9S43/1OkVAEqMweTvz1BkcCnHrAzRJkrxnlPOh9KBmNxOOGAJsKYW6EbEMf8Xz4/9C3sIbmRJQFRsqe7qwQ==</ds:SignatureValue>
                <ds:KeyInfo>
                    <ds:X509Data>
                        <ds:X509Certificate>MIIDXTCCAkWgAwIBAgIJALmVVuDWu4NYMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwHhcNMTYxMjMxMTQzNDQ3WhcNNDgwNjI1MTQzNDQ3WjBFMQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzUCFozgNb1h1M0jzNRSCjhOBnR+uVbVpaWfXYIR+AhWDdEe5ryY+CgavOg8bfLybyzFdehlYdDRgkedEB/GjG8aJw06l0qF4jDOAw0kEygWCu2mcH7XOxRt+YAH3TVHa/Hu1W3WjzkobqqqLQ8gkKWWM27fOgAZ6GieaJBN6VBSMMcPey3HWLBmc+TYJmv1dbaO2jHhKh8pfKw0W12VM8P1PIO8gv4Phu/uuJYieBWKixBEyy0lHjyixYFCR12xdh4CA47q958ZRGnnDUGFVE1QhgRacJCOZ9bd5t9mr8KLaVBYTCJo5ERE8jymab5dPqe5qKfJsCZiqWglbjUo9twIDAQABo1AwTjAdBgNVHQ4EFgQUxpuwcs/CYQOyui+r1G+3KxBNhxkwHwYDVR0jBBgwFoAUxpuwcs/CYQOyui+r1G+3KxBNhxkwDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAAiWUKs/2x/viNCKi3Y6blEuCtAGhzOOZ9EjrvJ8+COH3Rag3tVBWrcBZ3/uhhPq5gy9lqw4OkvEws99/5jFsX1FJ6MKBgqfuy7yh5s1YfM0ANHYczMmYpZeAcQf2CGAaVfwTTfSlzNLsF2lW/ly7yapFzlYSJLGoVE+OHEu8g5SlNACUEfkXw+5Eghh+KzlIN7R6Q7r2ixWNFBC/jWf7NKUfJyX8qIG5md1YUeT6GBW9Bm2/1/RiO24JTaYlfLdKK9TYb8sG5B+OLab2DImG99CJ25RkAcSobWNF5zD0O6lgOo3cEdB/ksCq3hmtlC/DlLZ/D8CJ+7VuZnS1rR2naQ==</ds:X509Certificate>
                    </ds:X509Data>
                </ds:KeyInfo>
            </ds:Signature>
            <samlp:Status>
                <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success" />
            </samlp:Status>
            <saml:Assertion xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                            xmlns:xs="http://www.w3.org/2001/XMLSchema"
                            ID="_efca8eaa2499ca65cfd6d153b9e9e873cf0a949368"
                            Version="2.0"
                            IssueInstant="{datetime.strftime(timestamp, timestamp_fmt)}"
                            >
                <saml:Issuer>http://myidp.com/some/path/to/metadata.php</saml:Issuer>
                <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                    <ds:SignedInfo>
                        <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
                        <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" />
                        <ds:Reference URI="#_efca8eaa2499ca65cfd6d153b9e9e873cf0a949368">
                            <ds:Transforms>
                                <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature" />
                                <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
                            </ds:Transforms>
                            <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
                            <ds:DigestValue>yO3xhwoBDgTXHXyJXOuxN9d+ZbI=</ds:DigestValue>
                        </ds:Reference>
                    </ds:SignedInfo>
                    <ds:SignatureValue>ErQMB6wSQ6U8PjZeG8GUX+O1GA5lwYN9sWC33+mjbs9i25TWDE1wjsWU2mnI7VZED0h0K8GkTwTItCCpScdJ8dh6g7lo1oXBz4N17l8Gd0RxUEt72MI/2F30Hkri13bZMegmPT2/BsdcgEh7ILRpaCWryyAyokz+TS9uoY+Lc0U88241wkj1r2TIFdtU6WxPlL12MaBOms3C3XJ4/R5d0salpAQ09ytcmMo11cZSIgPcRFQacRoUSDB+yZ04ld5FYaZ9S43/1OkVAEqMweTvz1BkcCnHrAzRJkrxnlPOh9KBmNxOOGAJsKYW6EbEMf8Xz4/9C3sIbmRJQFRsqe7qwQ==</ds:SignatureValue>
                    <ds:KeyInfo>
                        <ds:X509Data>
                            <ds:X509Certificate>MIIDXTCCAkWgAwIBAgIJALmVVuDWu4NYMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwHhcNMTYxMjMxMTQzNDQ3WhcNNDgwNjI1MTQzNDQ3WjBFMQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzUCFozgNb1h1M0jzNRSCjhOBnR+uVbVpaWfXYIR+AhWDdEe5ryY+CgavOg8bfLybyzFdehlYdDRgkedEB/GjG8aJw06l0qF4jDOAw0kEygWCu2mcH7XOxRt+YAH3TVHa/Hu1W3WjzkobqqqLQ8gkKWWM27fOgAZ6GieaJBN6VBSMMcPey3HWLBmc+TYJmv1dbaO2jHhKh8pfKw0W12VM8P1PIO8gv4Phu/uuJYieBWKixBEyy0lHjyixYFCR12xdh4CA47q958ZRGnnDUGFVE1QhgRacJCOZ9bd5t9mr8KLaVBYTCJo5ERE8jymab5dPqe5qKfJsCZiqWglbjUo9twIDAQABo1AwTjAdBgNVHQ4EFgQUxpuwcs/CYQOyui+r1G+3KxBNhxkwHwYDVR0jBBgwFoAUxpuwcs/CYQOyui+r1G+3KxBNhxkwDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAAiWUKs/2x/viNCKi3Y6blEuCtAGhzOOZ9EjrvJ8+COH3Rag3tVBWrcBZ3/uhhPq5gy9lqw4OkvEws99/5jFsX1FJ6MKBgqfuy7yh5s1YfM0ANHYczMmYpZeAcQf2CGAaVfwTTfSlzNLsF2lW/ly7yapFzlYSJLGoVE+OHEu8g5SlNACUEfkXw+5Eghh+KzlIN7R6Q7r2ixWNFBC/jWf7NKUfJyX8qIG5md1YUeT6GBW9Bm2/1/RiO24JTaYlfLdKK9TYb8sG5B+OLab2DImG99CJ25RkAcSobWNF5zD0O6lgOo3cEdB/ksCq3hmtlC/DlLZ/D8CJ+7VuZnS1rR2naQ==</ds:X509Certificate>
                        </ds:X509Data>
                    </ds:KeyInfo>
                </ds:Signature>
                <saml:Subject>
                    <saml:NameID SPNameQualifier="http://myhost/mysite/check_mk/saml_metadata.py"
                                 Format="urn:oasis:names:tc:SAML:2.0:nameid-format:transient"
                                 >_2697f8b9e1050e4d650a78087b01f482997982afcc</saml:NameID>
                    <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                        <saml:SubjectConfirmationData NotOnOrAfter="{datetime.strftime(valid_until, timestamp_fmt)}"
                                                      Recipient="http://myhost/mysite/check_mk/saml_acs.py?acs"
                                                      InResponseTo="{response_id}"
                                                      />
                    </saml:SubjectConfirmation>
                </saml:Subject>
                <saml:Conditions NotBefore="{datetime.strftime(timestamp, timestamp_fmt)}"
                                 NotOnOrAfter="{datetime.strftime(valid_until, timestamp_fmt)}"
                                 >
                    <saml:AudienceRestriction>
                        <saml:Audience>http://myhost/mysite/check_mk/saml_metadata.py</saml:Audience>
                    </saml:AudienceRestriction>
                </saml:Conditions>
                <saml:AuthnStatement AuthnInstant="{datetime.strftime(timestamp, timestamp_fmt)}"
                                     SessionNotOnOrAfter="{datetime.strftime(valid_until, timestamp_fmt)}"
                                     SessionIndex="_9f1f6e28ac623990bd1012437f6e03afdfa97e0399"
                                     >
                    <saml:AuthnContext>
                        <saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:Password</saml:AuthnContextClassRef>
                    </saml:AuthnContext>
                </saml:AuthnStatement>
                <saml:AttributeStatement>
                    <saml:Attribute Name="uid"
                                    NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic"
                                    >
                        <saml:AttributeValue xsi:type="xs:string">1</saml:AttributeValue>
                    </saml:Attribute>
                    <saml:Attribute Name="username"
                                    NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic"
                                    >
                        <saml:AttributeValue xsi:type="xs:string">user1</saml:AttributeValue>
                    </saml:Attribute>
                    <saml:Attribute Name="eduPersonAffiliation"
                                    NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic"
                                    >
                        <saml:AttributeValue xsi:type="xs:string">group1</saml:AttributeValue>
                    </saml:Attribute>
                    <saml:Attribute Name="email"
                                    NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic"
                                    >
                        <saml:AttributeValue xsi:type="xs:string">user1@example.com</saml:AttributeValue>
                    </saml:Attribute>
                </saml:AttributeStatement>
            </saml:Assertion>
        </samlp:Response>"""
    )


def bla(s, d, i, *args, **kwargs):
    return i


class TestInterface:
    @pytest.fixture(autouse=True)
    def ignore_signature(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "saml2.sigver.SecurityContext._check_signature", lambda s, d, i, *args, **kwargs: i
        )

    @pytest.fixture
    def interface(
        self,
        monkeypatch: pytest.MonkeyPatch,
        raw_config: dict[str, Any],
        config: SPConfig,
    ) -> Interface:
        monkeypatch.setattr(
            "cmk.gui.userdb.saml2.interface.raw_config_to_saml_config", lambda c: config
        )
        return Interface(raw_config)

    @pytest.fixture
    def request_id(self) -> str:
        return "1234567890"

    def test_interface_properties(self, interface: Interface) -> None:
        assert interface.acs_endpoint == (
            "http://myhost/mysite/check_mk/saml_acs.py?acs",
            "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
        )
        assert interface.acs_binding == (
            "http://myhost/mysite/check_mk/saml_acs.py?acs",
            "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
        )
        assert interface.idp_sso_binding == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        assert interface.idp_sso_destination == "http://myidp.com/some/path/to//SSOService.php"

    def test_metadata(self, interface: Interface, metadata: str) -> None:
        assert interface.metadata == metadata

    def test_authentication_request_is_valid(self, interface: Interface) -> None:
        request = str(interface.authentication_request(relay_state="index.py"))
        parsed_query = parse_qs(urlparse(request).query)

        relay_state = parsed_query.get("RelayState")
        saml_request = parsed_query.get("SAMLRequest")

        assert len(parsed_query) == 2

        assert relay_state == ["index.py"]

        assert isinstance(saml_request, list)
        assert len(saml_request) == 1

        saml_request_decoded = zlib.decompress(base64.b64decode(saml_request[0]), -15).decode(
            "utf-8"
        )
        assert re.search(VALID_AUTHENTICATION_REQUEST_PATTERN, saml_request_decoded)

    @pytest.mark.skip
    def test_parse_successful_authentication_request_response(
        self, interface: Interface, request_id: str
    ) -> None:
        parsed_response = interface.parse_authentication_request_response(
            _authentication_request_response(request_id), "index.py"
        )
        assert isinstance(parsed_response, Authenticated)
        assert parsed_response.in_response_to_id == request_id
        assert parsed_response.relay_state == "index.py"
        assert parsed_response.user_id == UserId("user1")

    @pytest.mark.skip
    def test_parse_authentication_request_response_outside_validity_window(
        self, interface: Interface, request_id: str
    ) -> None:
        now = datetime.utcnow()
        with pytest.raises(ResponseLifetimeExceed):
            interface.parse_authentication_request_response(
                _authentication_request_response(request_id, now, now - timedelta(days=5)),
                "index.py",
            )

    @pytest.mark.skip
    def test_parse_garbage_xml_authentication_request_response(self, interface: Interface) -> None:
        with pytest.raises(Exception) as e:
            interface.parse_authentication_request_response(
                _encode("<aardvark></aardvark>"), "index.py"
            )
        assert e.value.args[0] == "Unknown response type"

    @pytest.mark.skip
    def test_parse_garbage_authentication_request_response(self, interface: Interface) -> None:
        with pytest.raises(xml.etree.ElementTree.ParseError):
            interface.parse_authentication_request_response(_encode("aardvark"), "index.py")
