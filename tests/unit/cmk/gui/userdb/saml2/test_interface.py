#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import re
import time
import xml.etree.ElementTree as ET
from enum import Enum
from itertools import zip_longest
from pathlib import Path
from shutil import which
from typing import Any, Iterable

import lxml.html
import pytest
from freezegun import freeze_time
from lxml.html import HtmlElement
from redis import Redis
from saml2.client import Saml2Client
from saml2.cryptography.asymmetric import load_pem_private_key
from saml2.sigver import SignatureError
from saml2.validate import ResponseLifetimeExceed, ToEarly
from saml2.xmldsig import SIG_RSA_SHA1

from cmk.utils.redis import get_redis_client
from cmk.utils.type_defs import UserId

from cmk.gui.userdb.saml2.connector import ConnectorConfig
from cmk.gui.userdb.saml2.interface import (
    Authenticated,
    HTMLFormString,
    Interface,
    Milliseconds,
    saml_config,
)


class SAMLParamName(Enum):
    REQUEST = "SAMLRequest"
    RELAY_STATE = "RelayState"


def _encode(string: str) -> str:
    return base64.b64encode(string.encode("utf-8")).decode("utf-8")


def _decode(string: str) -> str:
    return base64.b64decode(string).decode("utf-8")


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


def _field_from_html(html_string: HTMLFormString, keyword: SAMLParamName) -> str:
    request = lxml.html.fromstring(html_string)
    assert isinstance(request, HtmlElement)
    message = dict(request.forms[0].fields).get(keyword.value)

    assert message is not None

    if keyword is SAMLParamName.RELAY_STATE:
        return message

    return _decode(message)


@pytest.fixture(scope="module", name="authentication_request")
def fixture_authentication_request(xml_files_path: Path) -> str:
    return _reduce_xml_template_whitespace(
        Path(xml_files_path / "authentication_request.xml").read_text()
    )


@pytest.fixture(scope="module", name="decoded_signed_authentication_request_response")
def fixture_decoded_signed_authentication_request_response(xml_files_path: Path) -> str:
    return _reconstruct_original_response_format(
        _reduce_xml_template_whitespace(
            Path(xml_files_path / "signed_authentication_request_response.xml").read_text()
        )
    )


@pytest.fixture(scope="module", name="signed_authentication_request_response")
def fixture_signed_authentication_request_response(
    decoded_signed_authentication_request_response: str,
) -> str:
    return _encode(decoded_signed_authentication_request_response)


class TestInterface:
    @pytest.fixture(autouse=True)
    def ignore_signature(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "saml2.sigver.SecurityContext._check_signature", lambda s, d, i, *args, **kwargs: i
        )

    @pytest.fixture(autouse=True)
    def initialised_redis(self) -> Iterable[Redis]:
        requests_db = get_redis_client()  # this is already monkeypatched to fakeredis
        requests_db.set(
            "saml2_authentication_requests:id-Ex1qiCa1tiZj1nBKe",
            "http://localhost:8080/simplesaml/saml2/idp/metadata.php",
        )
        yield requests_db

    @pytest.fixture
    def interface(
        self, metadata_from_idp: None, raw_config: dict[str, Any], initialised_redis: Redis
    ) -> Interface:
        config = ConnectorConfig(**raw_config).interface_config
        interface = Interface(config=config, requests_db=initialised_redis)

        # SHA1 is normally disallowed, but used in the test data for performance reasons
        interface._allowed_algorithms.add(SIG_RSA_SHA1)
        interface._authentication_request_id_expiry = Milliseconds(-1)

        client_config = saml_config(
            timeout=config.connection_timeout,
            idp_metadata_endpoint=config.idp_metadata_endpoint,
            checkmk_server_url=config.checkmk_server_url,
            signature_private_keyfile=config.signature_certificate.private,
            signature_public_keyfile=config.signature_certificate.public,
        )
        # The below suppressions are due to a bug with the typing extensions of the pysaml2
        # dependency. They can be removed once the typing extension package has been upgraded to
        # include https://github.com/cex-solutions/types-pysaml2/pull/59
        client_config.setattr("sp", "authn_requests_signed", False)  # type: ignore
        client_config.setattr("sp", "want_assertions_signed", False)  # type: ignore
        client_config.setattr("sp", "want_response_signed", False)  # type: ignore
        interface._client = Saml2Client(client_config)

        return interface

    @pytest.fixture
    def authentication_request_response_not_for_us(
        self, signed_authentication_request_response: str
    ) -> str:
        response = signed_authentication_request_response.replace(
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
        self, signed_authentication_request_response: str, request: pytest.FixtureRequest
    ) -> str:
        response = signed_authentication_request_response.replace(
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
        self, decoded_signed_authentication_request_response: str, request: pytest.FixtureRequest
    ) -> str:
        response = decoded_signed_authentication_request_response.split("\n")

        original_value, new_value, replacement_criteria = request.param

        modified_response = []
        for line in response:
            if replacement_criteria is None or replacement_criteria in line:
                line = line.replace(original_value, new_value)
            modified_response.append(line)

        return _encode("\n".join(modified_response))

    def test_interface_properties(self, interface: Interface) -> None:
        assert interface.acs_endpoint == "http://localhost/heute/check_mk/saml_acs.py?acs"
        assert interface.acs_binding == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        assert interface.idp_sso_binding == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        assert (
            interface.idp_sso_destination
            == "http://localhost:8080/simplesaml/saml2/idp/SSOService.php"
        )

    def test_metadata(self, interface: Interface, xml_files_path: Path) -> None:
        metadata = _reduce_xml_template_whitespace(
            Path(xml_files_path / "checkmk_service_provider_metadata.xml").read_text()
        )

        assert list((e.tag for e in ET.fromstring(interface.metadata).iter())) == list(
            (e.tag for e in ET.fromstring(metadata).iter())
        )

    def test_authentication_request_contains_relay_state(self, interface: Interface) -> None:
        relay_state = _field_from_html(
            html_string=interface.authentication_request(relay_state="index.py").data,
            keyword=SAMLParamName.RELAY_STATE,
        )

        assert relay_state == "index.py"

    def test_authentication_request_is_valid(
        self, interface: Interface, authentication_request: str
    ) -> None:
        dynamic_elements = {
            "ID": re.compile("id-[a-zA-Z0-9]{17}"),
            "IssueInstant": re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"),
        }  # These regex patterns are just to simplify comparison, they are not meant to test the conformity/standard of these fields

        request = _field_from_html(
            html_string=interface.authentication_request(relay_state="_").data,
            keyword=SAMLParamName.REQUEST,
        )

        for actual_element, expected_element in zip_longest(
            sorted(ET.fromstring(request).items()),
            sorted(ET.fromstring(authentication_request).items()),
        ):
            if regex_to_match := dynamic_elements.get(actual_element[0]):
                assert re.match(regex_to_match, actual_element[1])
            else:
                assert actual_element == expected_element

    @freeze_time("2022-12-28T11:06:05Z")
    def test_parse_successful_authentication_request_response(
        self, interface: Interface, signed_authentication_request_response: str
    ) -> None:
        parsed_response = interface.parse_authentication_request_response(
            signed_authentication_request_response
        )
        assert isinstance(parsed_response, Authenticated)
        assert parsed_response.in_response_to_id == "id-Ex1qiCa1tiZj1nBKe"
        assert parsed_response.user_id == UserId("user1")

    @freeze_time("2022-12-28T11:11:36Z")
    def test_parse_authentication_request_response_too_old(
        self, interface: Interface, signed_authentication_request_response: str
    ) -> None:
        with pytest.raises(ResponseLifetimeExceed):
            interface.parse_authentication_request_response(signed_authentication_request_response)

    @freeze_time("2022-12-28T11:06:04Z")
    def test_parse_authentication_request_response_too_young(
        self,
        interface: Interface,
        signed_authentication_request_response: str,
        ignore_signature: None,
    ) -> None:
        with pytest.raises(ToEarly):
            interface.parse_authentication_request_response(signed_authentication_request_response)

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
        self, interface: Interface, unsolicited_authentication_request_response: str
    ) -> None:
        with pytest.raises(AttributeError):
            interface.parse_authentication_request_response(
                unsolicited_authentication_request_response
            )

    def test_authentication_request_ids_expire(self, interface: Interface) -> None:
        redis = get_redis_client()  # this is already monkeypatched to fakeredis
        interface._redis_requests_db = redis

        expiry = 1
        interface._authentication_request_id_expiry = Milliseconds(expiry)

        interface.authentication_request(relay_state="_")

        time.sleep(expiry / 1000)

        assert not list(redis.keys("saml2_authentication_requests:*"))


@pytest.mark.skipif(not which("xmlsec1"), reason="Needs xmlsec1 to run")
class TestInterfaceSecurityFeatures:
    @pytest.fixture(scope="class", name="signature_certificate")
    def fixture_signature_certificate(
        self, signature_certificate_paths: tuple[Path, Path]
    ) -> Iterable[dict[str, str]]:
        private_keyfile_path, public_keyfile_path = signature_certificate_paths

        private_key_content = private_keyfile_path.read_bytes()
        public_key_content = public_keyfile_path.read_text()

        # The following awkwardness is done for performance reasons to patch a few slow spots with the
        # pysaml2 client. Note:

        # - 'load_pem_private_key' takes ages (!)
        # - the public key is somehow expected without a header by subsequent functions within the
        #   pysaml2 module
        in_memory_variant = {
            str(private_keyfile_path): load_pem_private_key(private_key_content),
            str(public_keyfile_path): "".join(public_key_content.splitlines()[1:-1]),
        }

        yield in_memory_variant

    @pytest.fixture(autouse=True)
    def certificates(
        self, monkeypatch: pytest.MonkeyPatch, signature_certificate: dict[str, str]
    ) -> None:
        monkeypatch.setattr(
            "saml2.sigver.import_rsa_key_from_file",
            lambda f: signature_certificate[f],
        )
        monkeypatch.setattr("saml2.cert.read_cert_from_file", lambda f, _: signature_certificate[f])
        monkeypatch.setattr(
            "saml2.sigver.read_cert_from_file", lambda f, _: signature_certificate[f]
        )
        monkeypatch.setattr(
            "saml2.metadata.read_cert_from_file",
            lambda f, *_: signature_certificate.get(
                f
            ),  # the .get method is used because encryption certificates are not yet implemented
        )

    @pytest.fixture
    def initialised_redis(self) -> Iterable[Redis]:
        requests_db = get_redis_client()  # this is already monkeypatched to fakeredis
        requests_db.set(
            "saml2_authentication_requests:id-Ex1qiCa1tiZj1nBKe",
            "http://localhost:8080/simplesaml/saml2/idp/metadata.php",
        )
        yield requests_db

    @pytest.fixture
    def interface(
        self, metadata_from_idp: None, raw_config: dict[str, Any], initialised_redis: Redis
    ) -> Interface:
        return Interface(
            config=ConnectorConfig(**raw_config).interface_config, requests_db=initialised_redis
        )

    @pytest.fixture
    def unsigned_authentication_request_response(self, xml_files_path: Path) -> str:
        return _encode(
            Path(xml_files_path / "unsigned_authentication_request_response.xml").read_text()
        )

    @pytest.fixture
    def malicious_authentication_request_response(
        self, decoded_signed_authentication_request_response: str
    ) -> str:
        malicious_response = decoded_signed_authentication_request_response.replace(
            "user1", "mwahahaha"
        )
        return _encode(malicious_response)

    def test_interface_properties_are_secure(self, interface: Interface) -> None:
        assert interface._client.authn_requests_signed is True
        assert interface._client.want_response_signed is True
        assert interface._client.want_assertions_signed is True

    @freeze_time("2022-12-28T11:06:05Z")
    def test_authentication_request_is_signed(
        self, interface: Interface, initialised_redis: Redis
    ) -> None:
        request = ET.fromstring(
            _field_from_html(
                html_string=interface.authentication_request(relay_state="_").data,
                keyword=SAMLParamName.REQUEST,
            )
        )

        tags = {"DigestValue", "SignatureValue", "X509Certificate"}
        signature_elements = {
            re.sub("\\{.*\\}", "", element.tag): element.text
            for element in request.iter()
            if any(element.tag.endswith(t) for t in tags)
        }

        assert len(tags) == len(signature_elements)
        assert signature_elements["DigestValue"]
        assert signature_elements["SignatureValue"]
        assert signature_elements["X509Certificate"]

    @freeze_time("2022-12-28T11:06:05Z")
    def test_parse_signed_authentication_request_response(
        self,
        interface: Interface,
        signed_authentication_request_response: str,
        initialised_redis: Redis,
    ) -> None:
        # SHA1 is normally disallowed, but used in the test data for performance reasons
        interface._allowed_algorithms.add(SIG_RSA_SHA1)
        parsed_response = interface.parse_authentication_request_response(
            signed_authentication_request_response
        )
        assert isinstance(parsed_response, Authenticated)

    def test_reject_unsigned_authentication_request_response(
        self, interface: Interface, unsigned_authentication_request_response: str
    ) -> None:
        with pytest.raises(SignatureError):
            interface.parse_authentication_request_response(
                unsigned_authentication_request_response
            )

    def test_reject_malicious_authentication_request_response(
        self, interface: Interface, malicious_authentication_request_response: str
    ) -> None:
        with pytest.raises(SignatureError):
            interface.parse_authentication_request_response(
                malicious_authentication_request_response
            )

    @freeze_time("2022-12-28T11:06:05Z")
    def test_rejected_authentication_response_if_signed_with_disallowed_algorithm(
        self, interface: Interface, signed_authentication_request_response: str
    ) -> None:
        with pytest.raises(AttributeError, match="Insecure algorithm"):
            interface.parse_authentication_request_response(signed_authentication_request_response)
