#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import re
import time
import xml.etree.ElementTree as ET
import zlib
from itertools import zip_longest
from pathlib import Path
from shutil import which
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

import pytest
from freezegun import freeze_time
from redis import Redis
from saml2.sigver import SignatureError
from saml2.validate import ResponseLifetimeExceed, ToEarly
from saml2.xmldsig import SIG_RSA_SHA1

from cmk.utils.redis import get_redis_client
from cmk.utils.type_defs import UserId

from cmk.gui.userdb.saml2.connector import ConnectorConfig
from cmk.gui.userdb.saml2.interface import Authenticated, Interface, Milliseconds

needs_xmlsec1 = pytest.mark.skipif(not which("xmlsec1"), reason="Needs xmlsec1 to run")


def _encode(string: str) -> str:
    return base64.b64encode(string.encode("utf-8")).decode("utf-8")


def _decode(string: str) -> str:
    return zlib.decompress(base64.b64decode(string), -15).decode("utf-8")


def _reduce_xml_template_whitespace(template: str) -> str:
    # This is to simplify comparison by adjusting the format to the one the pysaml2 client
    # generates
    return " ".join(template.split()).replace("> <", "><")


def _reconstruct_original_response_format(response: str) -> str:
    # The format must be exact for the digest to match the data.
    for string, replacement in {
        "<ds:SignedInfo": "\n  <ds:SignedInfo",
        "<ds:SignatureMethod": "\n    <ds:SignatureMethod",
        "<ds:Reference": "\n  <ds:Reference",
        "<ds:KeyInfo": "\n<ds:KeyInfo",
    }.items():
        response = response.replace(string, replacement)
    return response


class TestInterface:
    @pytest.fixture
    def ignore_signature(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "saml2.sigver.SecurityContext._check_signature", lambda s, d, i, *args, **kwargs: i
        )

    @pytest.fixture(autouse=True)
    def initialised_redis(self, monkeypatch: pytest.MonkeyPatch) -> Iterable[Redis]:
        requests_db = get_redis_client()  # this is already monkeypatched to fakeredis
        requests_db.set(
            "saml2_authentication_requests:id-Ex1qiCa1tiZj1nBKe",
            "http://localhost:8080/simplesaml/saml2/idp/metadata.php",
        )
        monkeypatch.setattr(
            "cmk.gui.userdb.saml2.interface.AUTHORIZATION_REQUEST_ID_DATABASE", requests_db
        )
        yield requests_db

    @pytest.fixture
    def ignore_sign_statement(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "saml2.sigver.CryptoBackendXmlSec1.sign_statement",
            lambda s, st, *args, **kwargs: st.decode("utf-8"),
        )

    @pytest.fixture
    def metadata(self, xml_files_path: Path) -> str:
        return _reduce_xml_template_whitespace(
            Path(xml_files_path / "checkmk_service_provider_metadata.xml").read_text()
        )

    @pytest.fixture
    def interface(self, metadata_from_idp: None, raw_config: dict[str, Any]) -> Interface:
        interface = Interface(ConnectorConfig(**raw_config).interface_config)
        interface.authentication_request_id_expiry = Milliseconds(-1)
        # SHA1 is normally disallowed, but used in the test data
        interface._allowed_algorithms.add(SIG_RSA_SHA1)
        return interface

    @pytest.fixture
    def secure_interface(self, metadata_from_idp: None, raw_config: dict[str, Any]) -> Interface:
        interface = Interface(ConnectorConfig(**raw_config).interface_config)
        interface.authentication_request_id_expiry = Milliseconds(-1)
        return Interface(ConnectorConfig(**raw_config).interface_config)

    @pytest.fixture
    def authentication_request(self, xml_files_path: Path) -> str:
        return _reduce_xml_template_whitespace(
            Path(xml_files_path / "authentication_request.xml").read_text()
        )

    @pytest.fixture
    def authentication_request_response(self, xml_files_path: Path) -> str:
        return _encode(
            _reconstruct_original_response_format(
                _reduce_xml_template_whitespace(
                    Path(xml_files_path / "authentication_request_response.xml").read_text()
                )
            )
        )

    @pytest.fixture
    def unsigned_authentication_request_response(self, xml_files_path: Path) -> str:
        return _encode(
            Path(xml_files_path / "unsigned_authentication_request_response.xml").read_text()
        )

    @pytest.fixture
    def malicious_authentication_request_response(self, xml_files_path: Path) -> str:
        original_response = _reconstruct_original_response_format(
            _reduce_xml_template_whitespace(
                Path(xml_files_path / "authentication_request_response.xml").read_text()
            )
        )
        malicious_response = original_response.replace("user1", "mwahahaha")
        return _encode(malicious_response)

    @pytest.fixture
    def authentication_request_response_not_for_us(self, xml_files_path: Path) -> str:
        response = Path(xml_files_path / "authentication_request_response.xml").read_text()
        response = response.replace(
            "<saml:Audience>http://localhost/heute/check_mk/saml_metadata.py</saml:Audience>",
            "<saml:Audience>http://some_other_audience.com</saml:Audience>",
        )
        return _encode(response)

    @pytest.fixture(
        params=[
            '<saml:Condition xsi:type="xs:string">mycustomconditiion</saml:Condition>',
            "<saml:Condition>mycustomconditiion</saml:Condition>",
        ],
        ids=[
            "Valid custom condition",
            "Custom condition not well-formed (must have xsi:type defined)",
        ],
    )
    def authentication_request_response_custom_condition(
        self, xml_files_path: Path, request: pytest.FixtureRequest
    ) -> str:
        response = Path(xml_files_path / "authentication_request_response.xml").read_text()
        response = response.replace(
            "</saml:Conditions>",
            f"{request.param}</saml:Conditions>",
        )
        return _encode(response)

    @pytest.fixture(
        params=[
            ('InResponseTo="id-Ex1qiCa1tiZj1nBKe"', "", None),
            ('InResponseTo="id-Ex1qiCa1tiZj1nBKe"', 'InResponseTo=""', None),
            ('InResponseTo="id-Ex1qiCa1tiZj1nBKe"', 'InResponseTo="id-12345678901234567"', None),
            (
                'InResponseTo="id-Ex1qiCa1tiZj1nBKe"',
                'InResponseTo="id-12345678901234567"',
                "SubjectConfirmationData",
            ),
            (
                "<saml:Issuer>http://localhost:8080/simplesaml/saml2/idp/metadata.php</saml:Issuer>",
                "<saml:Issuer>http://hackerman</saml:Issuer>",
                None,
            ),
        ],
        ids=[
            "No InResponseTo ID",
            "Empty value for InResponseTo ID",
            "Unknown InResponseTo ID",
            "Inconsistent InResponseTo ID",
            "Unexpected entity issued response",
        ],
    )
    def unsolicited_authentication_request_response(
        self, xml_files_path: Path, request: pytest.FixtureRequest
    ) -> str:
        with open(xml_files_path / "authentication_request_response.xml", "r") as f:
            response = f.readlines()

        original_value, new_value, replacement_criteria = request.param

        modified_response = []
        for line in response:
            if replacement_criteria is None or replacement_criteria in line:
                line = line.replace(original_value, new_value)
            modified_response.append(line)

        return _encode("\n".join(modified_response))

    def test_interface_properties(self, interface: Interface) -> None:
        assert interface.acs_endpoint == (
            "http://localhost/heute/check_mk/saml_acs.py?acs",
            "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
        )
        assert interface.acs_binding == (
            "http://localhost/heute/check_mk/saml_acs.py?acs",
            "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
        )
        assert interface.idp_sso_binding == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        assert (
            interface.idp_sso_destination
            == "http://localhost:8080/simplesaml/saml2/idp/SSOService.php"
        )

    def test_interface_properties_are_secure(self, interface: Interface) -> None:
        assert interface.want_response_signed is True
        assert interface.want_assertions_signed is True
        assert interface.authn_requests_signed is True

    def test_metadata(self, interface: Interface, metadata: str) -> None:
        assert list((e.tag for e in ET.fromstring(interface.metadata).iter())) == list(
            (e.tag for e in ET.fromstring(metadata).iter())
        )

    def test_authentication_request_contains_relay_state(
        self, interface: Interface, ignore_sign_statement: None
    ) -> None:
        request = str(interface.authentication_request(relay_state="index.py"))
        parsed_query = parse_qs(urlparse(request).query)

        relay_state = parsed_query.get("RelayState")

        assert relay_state == ["index.py"]

    def test_authentication_request_is_valid(
        self, interface: Interface, authentication_request: str, ignore_sign_statement: None
    ) -> None:
        dynamic_elements = {
            "ID": re.compile("id-[a-zA-Z0-9]{17}"),
            "IssueInstant": re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"),
        }  # These regex patterns are just to simplify comparison, they are not meant to test the conformity/standard of these fields

        request = str(interface.authentication_request(relay_state="_"))
        parsed_query = parse_qs(urlparse(request).query)

        saml_request = parsed_query.get("SAMLRequest")

        assert isinstance(saml_request, list)
        assert len(saml_request) == 1

        for actual_element, expected_element in zip_longest(
            sorted(ET.fromstring(_decode(saml_request[0])).items()),
            sorted(ET.fromstring(authentication_request).items()),
        ):
            if regex_to_match := dynamic_elements.get(actual_element[0]):
                assert re.match(regex_to_match, actual_element[1])
            else:
                assert actual_element == expected_element

    @freeze_time("2022-12-28T11:06:05Z")
    def test_parse_successful_authentication_request_response(
        self,
        interface: Interface,
        authentication_request_response: str,
        ignore_signature: None,
    ) -> None:
        parsed_response = interface.parse_authentication_request_response(
            authentication_request_response
        )
        assert isinstance(parsed_response, Authenticated)
        assert parsed_response.in_response_to_id == "id-Ex1qiCa1tiZj1nBKe"
        assert parsed_response.user_id == UserId("user1")

    @freeze_time("2022-12-28T11:11:36Z")
    def test_parse_authentication_request_response_too_old(
        self,
        interface: Interface,
        authentication_request_response: str,
        ignore_signature: None,
    ) -> None:
        with pytest.raises(ResponseLifetimeExceed):
            interface.parse_authentication_request_response(authentication_request_response)

    @freeze_time("2022-12-28T11:06:04Z")
    def test_parse_authentication_request_response_too_young(
        self,
        interface: Interface,
        authentication_request_response: str,
        ignore_signature: None,
    ) -> None:
        with pytest.raises(ToEarly):
            interface.parse_authentication_request_response(authentication_request_response)

    def test_parse_garbage_xml_authentication_request_response(self, interface: Interface) -> None:
        with pytest.raises(Exception):
            interface.parse_authentication_request_response(_encode("<aardvark></aardvark>"))

    def test_parse_garbage_authentication_request_response(self, interface: Interface) -> None:
        with pytest.raises(ET.ParseError):
            interface.parse_authentication_request_response(_encode("aardvark"))

    @freeze_time("2022-12-28T11:06:05Z")
    def test_parse_authentication_request_response_is_not_for_us(
        self,
        interface: Interface,
        authentication_request_response_not_for_us: str,
    ) -> None:
        with pytest.raises(Exception):
            interface.parse_authentication_request_response(
                authentication_request_response_not_for_us
            )

    @freeze_time("2022-12-28T11:06:05Z")
    def test_parse_authentication_request_response_custom_condition(
        self,
        interface: Interface,
        authentication_request_response_custom_condition: str,
    ) -> None:
        with pytest.raises(Exception):
            interface.parse_authentication_request_response(
                authentication_request_response_custom_condition
            )

    @freeze_time("2022-12-28T11:06:05Z")
    def test_reject_unsolicited_authentication_request_response(
        self,
        interface: Interface,
        unsolicited_authentication_request_response: str,
        ignore_signature: None,
    ) -> None:
        with pytest.raises(AttributeError):
            interface.parse_authentication_request_response(
                unsolicited_authentication_request_response
            )

    def test_authentication_request_ids_expire(
        self, interface: Interface, monkeypatch: pytest.MonkeyPatch, ignore_sign_statement: None
    ) -> None:
        redis = get_redis_client()  # this is already monkeypatched to fakeredis
        monkeypatch.setattr(
            "cmk.gui.userdb.saml2.interface.AUTHORIZATION_REQUEST_ID_DATABASE", redis
        )

        expiry = 1
        monkeypatch.setattr(interface, "authentication_request_id_expiry", expiry)

        interface.authentication_request(relay_state="_")

        time.sleep(expiry / 1000)

        assert not list(redis.keys("saml2_authentication_requests:*"))

    @freeze_time("2022-12-28T11:06:05Z")
    def test_authentication_request_id_is_deleted_once_accessed(
        self,
        interface: Interface,
        initialised_redis: Redis,
        authentication_request_response: str,
        ignore_signature: None,
    ) -> None:
        interface.parse_authentication_request_response(authentication_request_response)

        assert not list(initialised_redis.keys("saml2_authentication_requests:*"))

    @freeze_time("2022-12-28T11:06:05Z")
    @needs_xmlsec1
    def test_authentication_request_is_signed(self, interface: Interface) -> None:
        request = str(interface.authentication_request(relay_state="index.py"))
        parsed_query = ET.fromstring(_decode(parse_qs(urlparse(request).query)["SAMLRequest"][0]))

        tags = {"DigestValue", "SignatureValue", "X509Certificate"}
        signature_elements = {
            re.sub("\\{.*\\}", "", element.tag): element.text
            for element in parsed_query.iter()
            if any(element.tag.endswith(t) for t in tags)
        }

        assert len(tags) == len(signature_elements)
        assert signature_elements["DigestValue"]
        assert signature_elements["SignatureValue"]
        assert signature_elements["X509Certificate"]

    @needs_xmlsec1
    @freeze_time("2022-12-28T11:06:05Z")
    def test_parse_signed_authentication_request_response(
        self, interface: Interface, authentication_request_response: str
    ) -> None:
        parsed_response = interface.parse_authentication_request_response(
            authentication_request_response
        )
        assert isinstance(parsed_response, Authenticated)

    @needs_xmlsec1
    def test_reject_unsigned_authentication_request_response(
        self, interface: Interface, unsigned_authentication_request_response: str
    ) -> None:
        with pytest.raises(SignatureError):
            interface.parse_authentication_request_response(
                unsigned_authentication_request_response
            )

    @needs_xmlsec1
    def test_reject_malicious_authentication_request_response(
        self, interface: Interface, malicious_authentication_request_response: str
    ) -> None:
        with pytest.raises(SignatureError):
            interface.parse_authentication_request_response(
                malicious_authentication_request_response
            )

    @needs_xmlsec1
    @freeze_time("2022-12-28T11:06:05Z")
    def test_response_rejected_if_signed_with_disallowed_algorithm(
        self, secure_interface: Interface, authentication_request_response: str
    ) -> None:
        with pytest.raises(AttributeError, match="Insecure algorithm"):
            secure_interface.parse_authentication_request_response(authentication_request_response)
