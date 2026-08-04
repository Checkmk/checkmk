#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="explicit-override"

"""In-process SAML IdP mock for the user identity & auth composition tests.

A lightweight stand-in for the Keycloak container that authenticates the shared
:class:`Directory` users directly, so the SAML SSO tests run without Docker.
Mirrors :class:`KeycloakContainer`'s public surface so fixtures stay
backend-agnostic.
"""

from __future__ import annotations

import base64
import hashlib
import html
import http.cookies
import logging
import secrets
import socket
import tempfile
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, UTC
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import TracebackType
from typing import Any, Self
from urllib.parse import parse_qs, urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from lxml import etree  # type: ignore[import-untyped]

from cmk.crypto.certificate import CertificateWithPrivateKey, PersistedCertificateWithPrivateKey
from tests.system.multisite.identity.directory import Directory, DirectoryUser

_DS_NS = "http://www.w3.org/2000/09/xmldsig#"
_SAML_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
_SAMLP_NS = "urn:oasis:names:tc:SAML:2.0:protocol"

logger = logging.getLogger("identity-tests")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _generate_signing_keypair(out_dir: Path, common_name: str) -> tuple[Path, Path]:
    """Generate an RSA keypair and persist key + cert to disk (pysaml2 wants file paths)."""
    from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]

    bundle = CertificateWithPrivateKey.generate_self_signed(
        common_name=common_name,
        organization="Checkmk Mock SAML IdP",
        expiry=relativedelta(days=+30),
        key_size=2048,
    )
    key_path = out_dir / "idp.key.pem"
    cert_path = out_dir / "idp.cert.pem"
    PersistedCertificateWithPrivateKey.persist(bundle, cert_path, key_path)
    return key_path, cert_path


def _decode_authn_request(saml_request_b64: str) -> bytes:
    """Decode the SP's base64-encoded ``SAMLRequest`` (HTTP-POST binding)."""
    return base64.b64decode(saml_request_b64)


def _iso(dt: datetime) -> str:
    """ISO-8601 SAML-flavoured timestamp (UTC, no microseconds, ``Z`` suffix)."""
    return dt.replace(microsecond=0, tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compose_response_element(
    *,
    issuer: str,
    sp_entity_id: str,
    acs_url: str,
    in_response_to: str,
    uid: str,
    response_id: str,
    assertion_id: str,
    now: datetime,
    valid_for: timedelta,
) -> etree._Element:
    """Build an unsigned ``<samlp:Response>`` with one bearer ``<saml:Assertion>`` for ``uid``."""
    not_on_or_after = _iso(now + valid_for)
    now_str = _iso(now)
    nsmap = {"samlp": _SAMLP_NS, "saml": _SAML_NS}

    response = etree.Element(
        etree.QName(_SAMLP_NS, "Response"),
        nsmap=nsmap,
        attrib={
            "ID": response_id,
            "Version": "2.0",
            "IssueInstant": now_str,
            "Destination": acs_url,
            "InResponseTo": in_response_to,
        },
    )
    issuer_elem = etree.SubElement(response, etree.QName(_SAML_NS, "Issuer"))
    issuer_elem.text = issuer

    status = etree.SubElement(response, etree.QName(_SAMLP_NS, "Status"))
    etree.SubElement(
        status,
        etree.QName(_SAMLP_NS, "StatusCode"),
        Value="urn:oasis:names:tc:SAML:2.0:status:Success",
    )

    assertion = etree.SubElement(
        response,
        etree.QName(_SAML_NS, "Assertion"),
        attrib={"ID": assertion_id, "Version": "2.0", "IssueInstant": now_str},
    )
    a_issuer = etree.SubElement(assertion, etree.QName(_SAML_NS, "Issuer"))
    a_issuer.text = issuer

    subject = etree.SubElement(assertion, etree.QName(_SAML_NS, "Subject"))
    name_id = etree.SubElement(
        subject,
        etree.QName(_SAML_NS, "NameID"),
        Format="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent",
    )
    name_id.text = uid
    confirmation = etree.SubElement(
        subject,
        etree.QName(_SAML_NS, "SubjectConfirmation"),
        Method="urn:oasis:names:tc:SAML:2.0:cm:bearer",
    )
    etree.SubElement(
        confirmation,
        etree.QName(_SAML_NS, "SubjectConfirmationData"),
        InResponseTo=in_response_to,
        Recipient=acs_url,
        NotOnOrAfter=not_on_or_after,
    )

    conditions = etree.SubElement(
        assertion,
        etree.QName(_SAML_NS, "Conditions"),
        NotBefore=now_str,
        NotOnOrAfter=not_on_or_after,
    )
    audience_restriction = etree.SubElement(
        conditions, etree.QName(_SAML_NS, "AudienceRestriction")
    )
    audience = etree.SubElement(audience_restriction, etree.QName(_SAML_NS, "Audience"))
    audience.text = sp_entity_id

    authn_statement = etree.SubElement(
        assertion,
        etree.QName(_SAML_NS, "AuthnStatement"),
        AuthnInstant=now_str,
        SessionIndex=assertion_id,
    )
    authn_context = etree.SubElement(authn_statement, etree.QName(_SAML_NS, "AuthnContext"))
    accr = etree.SubElement(authn_context, etree.QName(_SAML_NS, "AuthnContextClassRef"))
    accr.text = "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"

    attr_statement = etree.SubElement(assertion, etree.QName(_SAML_NS, "AttributeStatement"))
    attribute = etree.SubElement(
        attr_statement,
        etree.QName(_SAML_NS, "Attribute"),
        Name="uid",
        NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
    )
    av = etree.SubElement(attribute, etree.QName(_SAML_NS, "AttributeValue"))
    av.text = uid

    return response


def _sign_element(
    element: etree._Element,
    private_key: rsa.RSAPrivateKey,
    cert_der: bytes,
) -> None:
    """RSA-SHA256 enveloped-signature over ``element`` (which must have an ``ID``), inserted after <Issuer>."""
    element_id = element.get("ID")
    if not element_id:
        raise ValueError("Element to sign must have an ID attribute")

    # Digest the element BEFORE inserting the Signature (enveloped-signature drops it).
    canonical = etree.tostring(element, method="c14n", exclusive=True, with_comments=False)
    digest_b64 = base64.b64encode(hashlib.sha256(canonical).digest()).decode("ascii")

    signed_info = etree.Element(etree.QName(_DS_NS, "SignedInfo"), nsmap={None: _DS_NS})
    etree.SubElement(
        signed_info,
        etree.QName(_DS_NS, "CanonicalizationMethod"),
        Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
    )
    etree.SubElement(
        signed_info,
        etree.QName(_DS_NS, "SignatureMethod"),
        Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
    )
    reference = etree.SubElement(
        signed_info, etree.QName(_DS_NS, "Reference"), URI=f"#{element_id}"
    )
    transforms = etree.SubElement(reference, etree.QName(_DS_NS, "Transforms"))
    etree.SubElement(
        transforms,
        etree.QName(_DS_NS, "Transform"),
        Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature",
    )
    etree.SubElement(
        transforms,
        etree.QName(_DS_NS, "Transform"),
        Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
    )
    etree.SubElement(
        reference,
        etree.QName(_DS_NS, "DigestMethod"),
        Algorithm="http://www.w3.org/2001/04/xmlenc#sha256",
    )
    digest_value = etree.SubElement(reference, etree.QName(_DS_NS, "DigestValue"))
    digest_value.text = digest_b64

    si_canonical = etree.tostring(signed_info, method="c14n", exclusive=True, with_comments=False)
    sig_bytes = private_key.sign(si_canonical, padding.PKCS1v15(), hashes.SHA256())
    signature_value_b64 = base64.b64encode(sig_bytes).decode("ascii")

    signature = etree.Element(etree.QName(_DS_NS, "Signature"), nsmap={None: _DS_NS})
    signature.append(signed_info)
    sv = etree.SubElement(signature, etree.QName(_DS_NS, "SignatureValue"))
    sv.text = signature_value_b64
    key_info = etree.SubElement(signature, etree.QName(_DS_NS, "KeyInfo"))
    x509_data = etree.SubElement(key_info, etree.QName(_DS_NS, "X509Data"))
    x509_cert = etree.SubElement(x509_data, etree.QName(_DS_NS, "X509Certificate"))
    x509_cert.text = base64.b64encode(cert_der).decode("ascii")

    # SAML core requires Signature right after <Issuer>.
    issuer_index = next(
        (i for i, child in enumerate(element) if etree.QName(child).localname == "Issuer"),
        None,
    )
    if issuer_index is None:
        element.insert(0, signature)
    else:
        element.insert(issuer_index + 1, signature)


def _build_idp_config(
    entity_id: str,
    sso_url: str,
    key_path: Path,
    cert_path: Path,
) -> dict[str, object]:
    """Build the pysaml2 ``IdPConfig`` dict (pure-Python XMLSecurity backend, in-memory only)."""
    from saml2 import BINDING_HTTP_POST  # type: ignore[import-not-found]
    from saml2.saml import NAME_FORMAT_URI  # type: ignore[import-not-found]

    return {
        "entityid": entity_id,
        "description": "Composition test mock SAML IdP",
        "service": {
            "idp": {
                "name": "Mock IdP",
                "endpoints": {
                    "single_sign_on_service": [(sso_url, BINDING_HTTP_POST)],
                },
                "policy": {
                    "default": {
                        "lifetime": {"hours": 1},
                        "attribute_restrictions": None,
                        "name_form": NAME_FORMAT_URI,
                    },
                },
                "want_authn_requests_signed": False,
                "sign_response": True,
                "sign_assertion": True,
            },
        },
        "key_file": str(key_path),
        "cert_file": str(cert_path),
        "crypto_backend": "XMLSecurity",  # pure-Python XMLDSig, no xmlsec1 binary
        "metadata": {},  # SPs registered programmatically via the mock
    }


class _MockSamlIdpHandler(BaseHTTPRequestHandler):
    """HTTP handler dispatching to the parent IdP (carried on ``server.mock_idp``)."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        logger.debug("mock-saml-idp %s — %s", self.address_string(), format % args)

    def _mock_idp(self) -> MockSamlIdp:
        assert isinstance(self.server, _MockSamlIdpHTTPServer)
        return self.server.mock_idp

    def do_GET(self) -> None:
        self._mock_idp()._dispatch(self, method="GET")

    def do_POST(self) -> None:
        self._mock_idp()._dispatch(self, method="POST")


class _MockSamlIdpHTTPServer(HTTPServer):
    """HTTPServer subclass carrying a back-reference to the mock IdP."""

    mock_idp: MockSamlIdp


class MockSamlIdp:
    """In-process stand-in for :class:`KeycloakContainer`."""

    REALM = "master"
    NETWORK_ALIAS = "comp-saml-idp"
    ADMIN_USER = "admin"
    ADMIN_PASSWORD = "admin"

    def __init__(
        self,
        directory: Directory,
        name: str = "mock-saml-idp",
    ) -> None:
        self.directory = directory
        self.name = name
        self.host_port: int = _free_port()
        self._tmp_dir = tempfile.TemporaryDirectory(prefix=f"{name}-")
        self._tmp_path = Path(self._tmp_dir.name)
        self._key_path, self._cert_path = _generate_signing_keypair(
            self._tmp_path,
            common_name=f"mock-saml-idp:{self.host_port}",
        )
        # Pre-load the keypair for the in-house XMLDSig signer; pysaml2 gets the file paths too.
        loaded_key = serialization.load_pem_private_key(self._key_path.read_bytes(), password=None)
        if not isinstance(loaded_key, rsa.RSAPrivateKey):
            raise TypeError("mock-saml-idp: signing key must be RSA")
        self._private_key: rsa.RSAPrivateKey = loaded_key
        self._certificate_der = x509.load_pem_x509_certificate(
            self._cert_path.read_bytes()
        ).public_bytes(serialization.Encoding.DER)
        self._sp_registrations: dict[str, list[str]] = {}  # entity_id -> accepted ACS URLs
        # cookie value -> authenticated uid; lets a shared Session skip the login form on reuse
        self._sessions: dict[str, str] = {}
        self._idp_lock = threading.Lock()
        # pysaml2 Server, built lazily (Any: not mypy-importable)
        self._idp_server: object | None = None
        RouteHandler = Callable[[_MockSamlIdpHandler, dict[str, list[str]]], None]
        self._routes: dict[tuple[str, str], RouteHandler] = {
            ("GET", f"/realms/{self.REALM}/protocol/saml/descriptor"): self._serve_metadata,
            ("POST", f"/realms/{self.REALM}/protocol/saml"): self._serve_sso,
        }
        self._http_server: _MockSamlIdpHTTPServer | None = None
        self._http_thread: threading.Thread | None = None

    def __enter__(self) -> Self:
        logger.info("Starting mock SAML IdP %s on 127.0.0.1:%d", self.name, self.host_port)
        self._http_server = _MockSamlIdpHTTPServer(
            ("127.0.0.1", self.host_port), _MockSamlIdpHandler
        )
        self._http_server.mock_idp = self
        self._http_thread = threading.Thread(target=self._http_server.serve_forever, name=self.name)
        self._http_thread.daemon = True
        self._http_thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        logger.info("Stopping mock SAML IdP %s", self.name)
        if self._http_server is not None:
            self._http_server.shutdown()
            self._http_server.server_close()
        if self._http_thread is not None:
            self._http_thread.join(timeout=5)
        self._tmp_dir.cleanup()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.host_port}"

    @property
    def metadata_url(self) -> str:
        return f"{self.base_url}/realms/{self.REALM}/protocol/saml/descriptor"

    @property
    def realm_url(self) -> str:
        return f"{self.base_url}/realms/{self.REALM}"

    @property
    def _sso_url(self) -> str:
        return f"{self.base_url}/realms/{self.REALM}/protocol/saml"

    @property
    def _entity_id(self) -> str:
        return f"{self.base_url}/realms/{self.REALM}"

    def fetch_metadata(self) -> str:
        """Return the IdP's SAML metadata XML (signed with the mock's keypair)."""
        from saml2.metadata import entity_descriptor  # type: ignore[import-not-found]

        return str(entity_descriptor(self._get_idp_server().config))

    def register_service_provider(self, entity_id: str, acs_urls: list[str]) -> None:
        """Record the SP's ACS URLs so AuthnRequests can be validated."""
        if not acs_urls:
            raise ValueError("acs_urls must contain at least one URL")
        self._sp_registrations[entity_id] = list(acs_urls)
        logger.info(
            "mock-saml-idp: registered SP %s with %d ACS URL(s)",
            entity_id,
            len(acs_urls),
        )

    def _dispatch(self, handler: _MockSamlIdpHandler, *, method: str) -> None:
        parsed = urlparse(handler.path)
        route = self._routes.get((method, parsed.path))
        if route is None:
            handler.send_response(404)
            handler.end_headers()
            handler.wfile.write(b"mock SAML IdP: no route for " + handler.path.encode())
            return
        try:
            route(handler, parse_qs(parsed.query))
        except Exception:
            logger.exception("mock-saml-idp: route %s %s raised", method, parsed.path)
            handler.send_response(500)
            handler.end_headers()
            handler.wfile.write(b"mock SAML IdP: handler error (see test log)")

    def _serve_metadata(
        self,
        handler: _MockSamlIdpHandler,
        _query: dict[str, list[str]],
    ) -> None:
        xml = self.fetch_metadata().encode("utf-8")
        handler.send_response(200)
        handler.send_header("Content-Type", "application/samlmetadata+xml")
        handler.send_header("Content-Length", str(len(xml)))
        handler.end_headers()
        handler.wfile.write(xml)

    def _serve_sso(
        self,
        handler: _MockSamlIdpHandler,
        _query: dict[str, list[str]],
    ) -> None:
        """SP-initiated SSO: no creds/session → login form; valid creds → set cookie + ACS form; existing session → silent ACS form."""
        size = int(handler.headers.get("Content-Length", 0))
        body = handler.rfile.read(size) if size > 0 else b""
        params = parse_qs(body.decode("utf-8"))
        if "SAMLRequest" not in params:
            handler.send_response(400)
            handler.end_headers()
            handler.wfile.write(b"mock SAML IdP: SAMLRequest missing")
            return

        saml_request_b64 = params["SAMLRequest"][0]
        relay_state = params.get("RelayState", [""])[0]
        cred_username = params.get("username", [None])[0]
        cred_password = params.get("password", [None])[0]

        session_uid = self._lookup_session(handler)
        cred_uid: str | None = None
        if cred_username is not None and cred_password is not None:
            user = self._authenticate(cred_username, cred_password)
            if user is None:
                self._send_html(
                    handler,
                    401,
                    f"<html><body>mock SAML IdP: invalid credentials for "
                    f"{html.escape(repr(cred_username))}</body></html>",
                )
                return
            cred_uid = user.uid

        # Fresh credential POST wins over an inherited session.
        uid = cred_uid or session_uid
        if uid is None:
            login_html = self._render_login_form(saml_request_b64, relay_state)
            self._send_html(handler, 200, login_html)
            return

        authn_request_xml = _decode_authn_request(saml_request_b64).decode("utf-8")
        sp_entity_id, in_response_to, acs_url = _parse_authn_request_basics(authn_request_xml)
        if acs_url is None:
            registered = self._sp_registrations.get(sp_entity_id)
            if not registered:
                raise RuntimeError(
                    f"mock-saml-idp: AuthnRequest for unregistered SP "
                    f"{sp_entity_id!r}; register via register_service_provider() first"
                )
            acs_url = registered[0]

        html_form = self._build_signed_response_form(
            sp_entity_id=sp_entity_id,
            acs_url=acs_url,
            in_response_to=in_response_to,
            relay_state=relay_state,
            uid=uid,
        )
        # Mint a session cookie only on a fresh credential POST; silent reuse must not rotate it.
        set_cookie: str | None = None
        if cred_uid is not None and session_uid != cred_uid:
            session_id = secrets.token_urlsafe(16)
            self._sessions[session_id] = cred_uid
            set_cookie = f"MOCK_IDP_SESSION={session_id}; Path=/realms/{self.REALM}; HttpOnly"
        self._send_html(handler, 200, html_form, set_cookie=set_cookie)

    def _lookup_session(self, handler: _MockSamlIdpHandler) -> str | None:
        """Return the uid associated with the request's session cookie, or None."""
        cookie_header = handler.headers.get("Cookie", "")
        if not cookie_header:
            return None
        jar = http.cookies.SimpleCookie(cookie_header)
        morsel = jar.get("MOCK_IDP_SESSION")
        if morsel is None:
            return None
        return self._sessions.get(morsel.value)

    def _render_login_form(self, saml_request_b64: str, relay_state: str) -> str:
        """Return an HTML login form that posts back to the SSO endpoint."""
        return (
            "<!DOCTYPE html><html><body>"
            "<h1>Mock SAML IdP</h1>"
            f"<form method='POST' action='{html.escape(self._sso_url)}'>"
            f"<input type='hidden' name='SAMLRequest' value='{html.escape(saml_request_b64)}'/>"
            f"<input type='hidden' name='RelayState' value='{html.escape(relay_state)}'/>"
            "<label>Username <input type='text' name='username'/></label>"
            "<label>Password <input type='password' name='password'/></label>"
            "<button type='submit'>Sign in</button>"
            "</form></body></html>"
        )

    def _authenticate(self, username: str, password: str) -> DirectoryUser | None:
        """Look the user up in the seeded directory and check the password."""
        for user in self.directory.users:
            if user.uid == username and user.password == password:
                return user
        return None

    @staticmethod
    def _send_html(
        handler: _MockSamlIdpHandler,
        status: int,
        html: str,
        *,
        set_cookie: str | None = None,
    ) -> None:
        body = html.encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        if set_cookie is not None:
            handler.send_header("Set-Cookie", set_cookie)
        handler.end_headers()
        handler.wfile.write(body)

    def _get_idp_server(self) -> Any:
        from saml2.config import IdPConfig  # type: ignore[import-not-found]
        from saml2.server import Server  # type: ignore[import-not-found]

        with self._idp_lock:
            if self._idp_server is None:
                cfg = IdPConfig()
                cfg.load(
                    _build_idp_config(
                        entity_id=self._entity_id,
                        sso_url=self._sso_url,
                        key_path=self._key_path,
                        cert_path=self._cert_path,
                    )
                )
                server = Server(config=cfg)
                # We carry no SP metadata and never encrypt, so short-circuit the lookup.
                server.has_encrypt_cert_in_metadata = lambda _sp: False
                self._idp_server = server
            return self._idp_server

    def _build_signed_response_form(
        self,
        *,
        sp_entity_id: str,
        acs_url: str,
        in_response_to: str,
        relay_state: str,
        uid: str,
    ) -> str:
        """Render an auto-submitting HTML form carrying a signed SAMLResponse (composed and signed via lxml + ``_sign_element``)."""
        from datetime import datetime, timedelta

        now = datetime.now(UTC)
        response_id = f"id-resp-{secrets.token_hex(8)}"
        assertion_id = f"id-assert-{secrets.token_hex(8)}"

        response_elem = _compose_response_element(
            issuer=self._entity_id,
            sp_entity_id=sp_entity_id,
            acs_url=acs_url,
            in_response_to=in_response_to,
            uid=uid,
            response_id=response_id,
            assertion_id=assertion_id,
            now=now,
            valid_for=timedelta(minutes=5),
        )

        # Sign the inner Assertion first: the outer Response signature must cover it.
        assertion_elem = response_elem.find(f"{{{_SAML_NS}}}Assertion")
        if assertion_elem is None:
            raise RuntimeError("mock-saml-idp: composed Response has no Assertion")
        _sign_element(assertion_elem, self._private_key, self._certificate_der)
        _sign_element(response_elem, self._private_key, self._certificate_der)

        signed_xml = etree.tostring(response_elem, encoding="utf-8", xml_declaration=False)
        response_b64 = base64.b64encode(signed_xml).decode("ascii")
        return (
            '<!DOCTYPE html><html><body onload="document.forms[0].submit()">'
            f"<form method='POST' action='{acs_url}'>"
            f"<input type='hidden' name='SAMLResponse' value='{response_b64}'/>"
            f"<input type='hidden' name='RelayState' value='{relay_state}'/>"
            "<noscript><button type='submit'>Continue</button></noscript>"
            "</form></body></html>"
        )


def _parse_authn_request_basics(xml: str) -> tuple[str, str, str | None]:
    """Regex out (sp_entity_id, request_id, requested_acs_url) from an AuthnRequest."""
    import re

    # Anchor on the local name only — pysaml2 varies the Issuer namespace prefix.
    sp_match = re.search(r"<(?:[\w]+:)?Issuer\b[^>]*>([^<]+)</(?:[\w]+:)?Issuer>", xml)
    if sp_match is None:
        raise RuntimeError(
            f"mock-saml-idp: AuthnRequest missing <Issuer>; body excerpt: {xml[:400]!r}"
        )
    sp_entity_id = sp_match.group(1)

    id_match = re.search(r'\bID="([^"]+)"', xml)
    if id_match is None:
        raise RuntimeError("mock-saml-idp: AuthnRequest missing ID attribute")
    request_id = id_match.group(1)

    acs_match = re.search(r'AssertionConsumerServiceURL="([^"]+)"', xml)
    acs_url = acs_match.group(1) if acs_match is not None else None

    return sp_entity_id, request_id, acs_url
