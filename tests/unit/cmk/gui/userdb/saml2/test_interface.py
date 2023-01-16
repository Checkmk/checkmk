#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping
from enum import Enum
from itertools import zip_longest
from pathlib import Path
from shutil import which
from typing import Final

import lxml.html
import pytest
from freezegun import freeze_time
from lxml.html import HtmlElement
from redis import Redis
from saml2 import BINDING_HTTP_POST
from saml2.cryptography.asymmetric import load_pem_private_key
from saml2.sigver import SignatureError
from saml2.validate import ResponseLifetimeExceed, ToEarly
from saml2.xmldsig import (
    DIGEST_SHA512,
    SIG_ECDSA_SHA256,
    SIG_ECDSA_SHA384,
    SIG_ECDSA_SHA512,
    SIG_RSA_SHA1,
    SIG_RSA_SHA256,
    SIG_RSA_SHA384,
    SIG_RSA_SHA512,
)

from cmk.utils.redis import get_redis_client
from cmk.utils.type_defs import UserId

from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb.saml2.config import (
    CacheSettings,
    Certificate,
    ConnectivitySettings,
    InterfaceConfig,
    Milliseconds,
    SecuritySettings,
    UserAttributeNames,
)
from cmk.gui.userdb.saml2.interface import (
    AuthenticatedUser,
    HTMLFormString,
    Interface,
    user_attributes_to_authenticated_user,
)


class SAMLParamName(Enum):
    REQUEST = "SAMLRequest"
    RELAY_STATE = "RelayState"


def signature_certificate_paths() -> Certificate:
    # Certificates are generated with 1024 bit for performance reasons. Command:
    # openssl req -x509 -newkey rsa:1024 -days +3650 -subj \
    # "/CN=saml2-test-sign/O=checkmk-testing/C=DE" -keyout signature_private.pem -out \
    # signature_public.pem -sha256 -nodes
    cert_dir = Path(__file__).parent / "certificate_files"
    return Certificate(
        private=Path(cert_dir / "signature_private.pem"),
        public=Path(cert_dir / "signature_public.pem"),
    )


def _reconstruct_original_response_format(response: bytes) -> bytes:
    # The format must be exact for the digest to match the data.
    response = b" ".join(response.split()).replace(b"> <", b"><")
    for string, replacement in {
        b"<ds:SignedInfo": b"\n  <ds:SignedInfo",
        b"<ds:SignatureMethod": b"\n    <ds:SignatureMethod",
        b"<ds:Reference": b"\n  <ds:Reference",
        b"<ds:KeyInfo": b"\n<ds:KeyInfo",
    }.items():
        response = response.replace(string, replacement)
    return response


_SIGNATURE_CERTIFICATE_PATHS: Final = signature_certificate_paths()
_XML_FILES_PATH: Final = Path(__file__).parent / "xml_files"
_IDENTITY_PROVIDER_METADATA: Final = Path(
    _XML_FILES_PATH / "identity_provider_metadata.xml"
).read_text()
_AUTHENTICATION_REQUEST: Final = Path(_XML_FILES_PATH / "authentication_request.xml").read_text()
_SIGNED_AUTHENTICATION_REQUEST_RESPONSE: Final = _reconstruct_original_response_format(
    Path(_XML_FILES_PATH / "signed_authentication_request_response.xml").read_bytes()
)
_UNSIGNED_AUTHENTICATION_REQUEST_RESPONSE: Final = Path(
    _XML_FILES_PATH / "unsigned_authentication_request_response.xml"
).read_bytes()


def _interface_config(
    *, do_security: bool = False, cache_expiry: Milliseconds = Milliseconds(-1)
) -> InterfaceConfig:
    if do_security:
        allowed_algorithms = {
            SIG_ECDSA_SHA256,
            SIG_ECDSA_SHA384,
            SIG_ECDSA_SHA512,
            SIG_RSA_SHA256,
            SIG_RSA_SHA384,
            SIG_RSA_SHA512,
        }
    else:
        allowed_algorithms = {SIG_RSA_SHA1}

    return InterfaceConfig(
        connectivity_settings=ConnectivitySettings(
            timeout=(12, 12),
            idp_metadata_endpoint="http://localhost:8080/simplesaml/saml2/idp/metadata.php",
            checkmk_server_url="http://localhost",
            entity_id="http://localhost/heute/check_mk/saml_metadata.py",
            assertion_consumer_service_endpoint="http://localhost/heute/check_mk/saml_acs.py?acs",
            binding=BINDING_HTTP_POST,
        ),
        user_attributes=UserAttributeNames(
            user_id="username",
            alias=None,
            email=None,
            contactgroups=None,
        ),
        security_settings=SecuritySettings(
            allow_unknown_user_attributes=True,
            sign_authentication_requests=do_security,
            enforce_signed_responses=do_security,
            enforce_signed_assertions=do_security,
            signing_algortithm=SIG_RSA_SHA512,
            digest_algorithm=DIGEST_SHA512,  # this is referring to the digest alg the counterparty should use
            allowed_algorithms=allowed_algorithms,
            signature_certificate=_SIGNATURE_CERTIFICATE_PATHS,
        ),
        cache_settings=CacheSettings(
            redis_namespace="saml2_authentication_requests",
            authentication_request_id_expiry=cache_expiry,
        ),
    )


def _encode(string: bytes) -> str:
    return base64.b64encode(string).decode("utf-8")


def _field_from_html(html_string: HTMLFormString, keyword: SAMLParamName) -> str:
    request = lxml.html.fromstring(html_string)
    assert isinstance(request, HtmlElement)
    message = dict(request.forms[0].fields).get(keyword.value)

    assert message is not None

    if keyword is SAMLParamName.RELAY_STATE:
        return message

    return base64.b64decode(message).decode("utf-8")


class TestInterface:
    @pytest.fixture(autouse=True)
    def xmlsec1_binary_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Mock that the xmlsec1 binary exists and is in PATH
        monkeypatch.setattr("saml2.sigver.get_xmlsec_binary", lambda p: "xmlsec1")
        monkeypatch.setattr("os.path.exists", lambda p: True)

    @pytest.fixture(autouse=True)
    def ignore_signature(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "saml2.sigver.SecurityContext._check_signature", lambda s, d, i, *args, **kwargs: i
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
    def interface(self, monkeypatch: pytest.MonkeyPatch, initialised_redis: Redis) -> Interface:
        # TODO (CMK-11997): this feature will allow me to circumvent this monkeypatched function
        monkeypatch.setattr(
            "cmk.gui.userdb.saml2.interface._metadata_from_idp",
            lambda c, t: _IDENTITY_PROVIDER_METADATA,
        )

        return Interface(_interface_config(do_security=False), initialised_redis)

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
        self, request: pytest.FixtureRequest
    ) -> str:
        response = _SIGNED_AUTHENTICATION_REQUEST_RESPONSE.replace(
            b"</saml:Conditions>",
            f"{request.param}</saml:Conditions>".encode("utf-8"),
        )
        return _encode(response)

    @pytest.fixture(
        params=[
            (b'InResponseTo="id-Ex1qiCa1tiZj1nBKe"', b"", None),
            (b'InResponseTo="id-Ex1qiCa1tiZj1nBKe"', b'InResponseTo=""', None),
            (b'InResponseTo="id-Ex1qiCa1tiZj1nBKe"', b'InResponseTo="id-12345678901234567"', None),
            (
                b'InResponseTo="id-Ex1qiCa1tiZj1nBKe"',
                b'InResponseTo="id-12345678901234567"',
                b"SubjectConfirmationData",
            ),
            (
                b"<saml:Issuer>http://localhost:8080/simplesaml/saml2/idp/metadata.php</saml:Issuer>",
                b"<saml:Issuer>http://hackerman</saml:Issuer>",
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
    def unsolicited_authentication_request_response(self, request: pytest.FixtureRequest) -> str:
        response = _SIGNED_AUTHENTICATION_REQUEST_RESPONSE.split(b"\n")

        original_value, new_value, replacement_criteria = request.param

        modified_response = []
        for line in response:
            if replacement_criteria is None or replacement_criteria in line:
                line = line.replace(original_value, new_value)
            modified_response.append(line)

        return _encode(b"\n".join(modified_response))

    def test_interface_properties(self, interface: Interface) -> None:
        assert interface.acs_endpoint == "http://localhost/heute/check_mk/saml_acs.py?acs"
        assert interface.acs_binding == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        assert interface.idp_sso_binding == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        assert (
            interface.idp_sso_destination
            == "http://localhost:8080/simplesaml/saml2/idp/SSOService.php"
        )

    def test_metadata(self, interface: Interface) -> None:
        metadata = Path(_XML_FILES_PATH / "checkmk_service_provider_metadata.xml").read_text()

        assert list((e.tag for e in ET.fromstring(interface.metadata).iter())) == list(
            (e.tag for e in ET.fromstring(metadata).iter())
        )

    def test_authentication_request_contains_relay_state(self, interface: Interface) -> None:
        relay_state = _field_from_html(
            html_string=interface.authentication_request(relay_state="index.py").data,
            keyword=SAMLParamName.RELAY_STATE,
        )

        assert relay_state == "index.py"

    def test_authentication_request_is_valid(self, interface: Interface) -> None:
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
            sorted(ET.fromstring(_AUTHENTICATION_REQUEST).items()),
        ):
            if regex_to_match := dynamic_elements.get(actual_element[0]):
                assert re.match(regex_to_match, actual_element[1])
            else:
                assert actual_element == expected_element

    @freeze_time("2022-12-28T11:06:05Z")
    def test_parse_successful_authentication_request_response(self, interface: Interface) -> None:
        parsed_response = interface.parse_authentication_request_response(
            _encode(_SIGNED_AUTHENTICATION_REQUEST_RESPONSE)
        )
        assert isinstance(parsed_response, AuthenticatedUser)
        assert parsed_response.user_id == UserId("user1")

    @freeze_time("2022-12-28T11:11:36Z")
    def test_parse_authentication_request_response_too_old(self, interface: Interface) -> None:
        with pytest.raises(ResponseLifetimeExceed):
            interface.parse_authentication_request_response(
                _encode(_SIGNED_AUTHENTICATION_REQUEST_RESPONSE)
            )

    @freeze_time("2022-12-28T11:06:04Z")
    def test_parse_authentication_request_response_too_young(self, interface: Interface) -> None:
        with pytest.raises(ToEarly):
            interface.parse_authentication_request_response(
                _encode(_SIGNED_AUTHENTICATION_REQUEST_RESPONSE)
            )

    def test_parse_garbage_xml_authentication_request_response(self, interface: Interface) -> None:
        with pytest.raises(Exception):
            interface.parse_authentication_request_response(_encode(b"<aardvark></aardvark>"))

    def test_parse_garbage_authentication_request_response(self, interface: Interface) -> None:
        with pytest.raises(ET.ParseError):
            interface.parse_authentication_request_response(_encode(b"aardvark"))

    @freeze_time("2022-12-28T11:06:05Z")
    def test_parse_authentication_request_response_is_not_for_us(
        self, interface: Interface
    ) -> None:
        response = _SIGNED_AUTHENTICATION_REQUEST_RESPONSE.replace(
            b"<saml:Audience>http://localhost/heute/check_mk/saml_metadata.py</saml:Audience>",
            b"<saml:Audience>http://some_other_audience.com</saml:Audience>",
        )

        with pytest.raises(Exception):
            interface.parse_authentication_request_response(_encode(response))

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
    def fixture_signature_certificate(self) -> Iterable[Mapping[str, str]]:
        private_key_content = _SIGNATURE_CERTIFICATE_PATHS.private.read_bytes()
        public_key_content = _SIGNATURE_CERTIFICATE_PATHS.public.read_text()
        # The following awkwardness is done for performance reasons to patch a few slow spots with the
        # pysaml2 client. Note:
        # - 'load_pem_private_key' takes ages (!)
        # - the public key is somehow expected without a header by subsequent functions within the
        #   pysaml2 module
        in_memory_variant = {
            str(_SIGNATURE_CERTIFICATE_PATHS.private): load_pem_private_key(private_key_content),
            str(_SIGNATURE_CERTIFICATE_PATHS.public): "".join(
                public_key_content.splitlines()[1:-1]
            ),
        }
        yield in_memory_variant

    @pytest.fixture(autouse=True)
    def certificates(
        self, monkeypatch: pytest.MonkeyPatch, signature_certificate: Mapping[str, str]
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
    def interface(self, monkeypatch: pytest.MonkeyPatch, initialised_redis: Redis) -> Interface:
        # TODO (CMK-11997): this feature will allow me to circumvent this monkeypatched function
        monkeypatch.setattr(
            "cmk.gui.userdb.saml2.interface._metadata_from_idp",
            lambda c, t: _IDENTITY_PROVIDER_METADATA,
        )

        return Interface(config=_interface_config(do_security=True), requests_db=initialised_redis)

    def test_interface_properties_are_secure(self, interface: Interface) -> None:
        assert interface._client.authn_requests_signed is True
        assert interface._client.want_response_signed is True
        assert interface._client.want_assertions_signed is True

    @freeze_time("2022-12-28T11:06:05Z")
    def test_authentication_request_is_signed(self, interface: Interface) -> None:
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
    def test_parse_signed_authentication_request_response(self, interface: Interface) -> None:
        # SHA1 is normally disallowed, but used in the test data for performance reasons
        interface._allowed_algorithms.add(SIG_RSA_SHA1)

        parsed_response = interface.parse_authentication_request_response(
            _encode(_SIGNED_AUTHENTICATION_REQUEST_RESPONSE)
        )
        assert isinstance(parsed_response, AuthenticatedUser)

    def test_reject_unsigned_authentication_request_response(self, interface: Interface) -> None:
        with pytest.raises(SignatureError):
            interface.parse_authentication_request_response(
                _encode(_UNSIGNED_AUTHENTICATION_REQUEST_RESPONSE)
            )

    def test_reject_malicious_authentication_request_response(self, interface: Interface) -> None:
        malicious_response = _SIGNED_AUTHENTICATION_REQUEST_RESPONSE.replace(b"user1", b"mwahahaha")

        with pytest.raises(SignatureError):
            interface.parse_authentication_request_response(_encode(malicious_response))

    @freeze_time("2022-12-28T11:06:05Z")
    def test_rejected_authentication_response_if_signed_with_disallowed_algorithm(
        self, interface: Interface
    ) -> None:
        with pytest.raises(AttributeError, match="Insecure algorithm"):
            interface.parse_authentication_request_response(
                _encode(_SIGNED_AUTHENTICATION_REQUEST_RESPONSE)
            )


def test_user_attributes_to_authenticated_user() -> None:
    user_attributes = {
        "username": ["banana"],
        "pretty_name": ["Mr. Banana"],
        "email_address": ["banana@totally-not-the-cia.com"],
        "groups": ["hottopics", "veryhottopics"],
    }
    default_user_profile = UserSpec(
        {
            "contactgroups": [],
            "force_authuser": False,
            "roles": ["user"],
        }
    )

    authenticated_user = user_attributes_to_authenticated_user(
        user_attribute_names=UserAttributeNames(
            user_id="username",
            alias="pretty_name",
            email="email_address",
            contactgroups="groups",
        ),
        user_id=UserId("banana"),
        user_attributes=user_attributes,
        default_user_profile=default_user_profile,
        checkmk_contact_groups={"hottopics"},
    )

    assert authenticated_user == UserSpec(
        {
            "user_id": UserId("banana"),
            "alias": "Mr. Banana",
            "email": "banana@totally-not-the-cia.com",
            "roles": ["user"],
            "contactgroups": ["hottopics"],
            "force_authuser": False,
        }
    )
