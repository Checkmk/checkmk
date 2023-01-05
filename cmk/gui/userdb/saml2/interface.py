#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Mapping, NewType

import requests
from pydantic import BaseModel
from redis.client import Pipeline
from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.client import Saml2Client
from saml2.config import SPConfig
from saml2.metadata import create_metadata_string
from saml2.response import AuthnResponse
from saml2.s_utils import UnknownSystemEntity
from saml2.saml import NAMEID_FORMAT_PERSISTENT
from saml2.xmldsig import (
    DIGEST_SHA512,
    SIG_ECDSA_SHA256,
    SIG_ECDSA_SHA384,
    SIG_ECDSA_SHA512,
    SIG_RSA_SHA256,
    SIG_RSA_SHA384,
    SIG_RSA_SHA512,
)

from cmk.utils.redis import get_redis_client, IntegrityCheckResponse, query_redis
from cmk.utils.site import url_prefix
from cmk.utils.type_defs import UserId

from cmk.gui.log import logger

LOGGER = logger.getChild("saml2")


XMLData = NewType("XMLData", str)
URLRedirect = NewType("URLRedirect", str)
RequestId = NewType("RequestId", str)
Milliseconds = NewType("Milliseconds", int)

AUTHORIZATION_REQUEST_ID_DATABASE = get_redis_client()


class Certificate(BaseModel):
    private: Path
    public: Path


class InterfaceConfig(BaseModel):
    connection_timeout: tuple[int, int]
    checkmk_server_url: str
    idp_metadata_endpoint: str
    user_id_attribute: str
    signature_certificate: Certificate


class Authenticated(BaseModel):
    user_id: UserId
    in_response_to_id: RequestId


def _metadata_from_idp(url: str, timeout: tuple[int, int]) -> str | None:
    # TODO (CMK-11851): IdP metadata changes rarely so the content should be cached.
    metadata = requests.get(url, verify=True, timeout=timeout)
    if metadata.status_code < 200 or metadata.status_code > 299:
        LOGGER.critical("Failed to fetch metadata from URL %s", url)
        return None
    return metadata.text


def saml_config(
    checkmk_server_url: str,
    idp_metadata_endpoint: str,
    timeout: tuple[int, int],
    signature_private_keyfile: Path,
    signature_public_keyfile: Path,
) -> SPConfig:
    """Convert valuespecs into a valid SAML Service Provider configuration."""
    config = SPConfig()
    checkmk_base_url = f"{checkmk_server_url}{url_prefix()}check_mk"
    acs_endpoint_url = f"{checkmk_base_url}/saml_acs.py?acs"
    sp_configuration = {
        "endpoints": {
            "assertion_consumer_service": [
                (acs_endpoint_url, BINDING_HTTP_REDIRECT),
                (acs_endpoint_url, BINDING_HTTP_POST),
            ]
        },
        "allow_unsolicited": True,
        "authn_requests_signed": True,
        "want_assertions_signed": True,
        "want_response_signed": True,
        "signing_algorithm": SIG_RSA_SHA512,
        "digest_algorithm": DIGEST_SHA512,  # this is referring to the digest alg the counterparty should use
    }
    config.load(
        {
            "entityid": f"{checkmk_base_url}/saml_metadata.py",
            "metadata": {"inline": [_metadata_from_idp(idp_metadata_endpoint, timeout)]},
            "service": {"sp": sp_configuration},
            "allow_unknown_attributes": True,
            "http_client_timeout": timeout,
            "key_file": str(signature_private_keyfile),
            "cert_file": str(signature_public_keyfile),
            "encryption_keypairs": [
                {
                    # TODO (CMK-11946): implement encryption
                    "key_file": "",
                    "cert_file": "",
                },
            ],
        }
    )
    return config


def attributes_mapping(user_id_attribute: str) -> Mapping[str, str]:
    """Map attribute fields the Identity Provider sends to fields we expect."""
    return {"user_id_attribute": user_id_attribute}


class Interface:
    def __init__(self, config: InterfaceConfig) -> None:
        self._config = saml_config(
            timeout=config.connection_timeout,
            idp_metadata_endpoint=config.idp_metadata_endpoint,
            checkmk_server_url=config.checkmk_server_url,
            signature_private_keyfile=config.signature_certificate.private,
            signature_public_keyfile=config.signature_certificate.public,
        )
        self._attributes_mapping = attributes_mapping(config.user_id_attribute)
        self._user_id_attribute = self._attributes_mapping["user_id_attribute"]
        self._client = Saml2Client(config=self._config)
        self._metadata = create_metadata_string(configfile=None, config=self._config).decode(
            "utf-8"
        )
        self._redis_namespace = "saml2_authentication_requests"
        self.authentication_request_id_expiry = Milliseconds(5 * 60 * 1000)

        # Maintaining an allow-list has the advantage of knowing exactly what we support, and we are
        # less prone to changes made to the pysaml2 dependency. New algorithms are not added
        # frequently.
        self._allowed_algorithms = {
            SIG_ECDSA_SHA256,
            SIG_ECDSA_SHA384,
            SIG_ECDSA_SHA512,
            SIG_RSA_SHA256,
            SIG_RSA_SHA384,
            SIG_RSA_SHA512,
        }

        self.acs_endpoint, self.acs_binding = self._config.getattr("endpoints")[
            "assertion_consumer_service"
        ]

        if self._config.metadata is None:
            raise AttributeError("Got no metadata information from Identity Provider")

        self._identity_provider_entity_id = list(self._config.metadata.keys())[
            0
        ]  # May or may not be the metadata endpoint of the IdP

        try:
            self.idp_sso_binding, self.idp_sso_destination = self._client.pick_binding(
                "single_sign_on_service",
                [BINDING_HTTP_REDIRECT, BINDING_HTTP_POST],
                "idpsso",
                entity_id=self._identity_provider_entity_id,
            )
        except UnknownSystemEntity:
            # TODO (CMK-11846): handle this
            raise UnknownSystemEntity

    @property
    def want_response_signed(self) -> bool:
        return self._client.want_response_signed

    @property
    def want_assertions_signed(self) -> bool:
        return self._client.want_assertions_signed

    @property
    def authn_requests_signed(self) -> bool:
        return self._client.authn_requests_signed

    @property
    def signing_algorithm(self) -> str:
        return self._client.signing_algorithm

    @property
    def digest_algorithm(self) -> str:
        return self._client.digest_algorithm

    @property
    def metadata(self) -> XMLData:
        """Entity ID that is registered with the Identity Provider and information about preferred
        bindings.

        Returns:
            A valid XML string
        """
        return XMLData(self._metadata)

    def authentication_request(self, relay_state: str) -> URLRedirect:
        """Authentication request to be forwarded to the Identity Provider.

        It is up to the Identity Provider to perform any authentication if the user is not already
        logged in.

        Additionally, the request IDs are tracked so that it can be verified that responses received
        are in response to a request that has actually been made.

        Args:
            relay_state: The URL the user originally requested and any other state information

        Returns:
            The URL, including the authentication request, that redirects the user to their Identity
            Provider's Single Sign-On service

        Raises:
            AttributeError: The redirect URL to the Identity Provider's Single Sign-On Service could
                not be created
        """

        def _redis_update_query(pipeline: Pipeline) -> None:
            hkey = f"{self._redis_namespace}:{authn_request_id}"
            pipeline.set(
                hkey,
                self._identity_provider_entity_id,
            )
            pipeline.pexpire(
                hkey,
                self.authentication_request_id_expiry,
            )

        LOGGER.debug("Prepare authentication request")
        authn_request_id, authn_request = self._client.create_authn_request(
            self.idp_sso_destination,
            binding=self.acs_binding,
            extensions=None,
            # TODO (lisa): find out what this option does
            nameid_format=NAMEID_FORMAT_PERSISTENT,
        )

        query_redis(
            client=AUTHORIZATION_REQUEST_ID_DATABASE,
            data_key=self._redis_namespace,
            integrity_callback=lambda: IntegrityCheckResponse.UPDATE,
            update_callback=_redis_update_query,
            query_callback=lambda: None,
            timeout=5,
        )

        http_headers = self._client.apply_binding(
            self.idp_sso_binding,
            authn_request,
            self.idp_sso_destination,
            relay_state=relay_state,
        )["headers"]

        if (url_redirect := dict(http_headers).get("Location")) is None:
            raise AttributeError("Unable to create redirect URL")

        LOGGER.debug("Redirect URL: %s", url_redirect)

        return URLRedirect(url_redirect)

    def parse_authentication_request_response(self, saml_response: str) -> Authenticated:
        """Parse responses received from the Identity Provider to authentication requests we made.

        Take into account the authentication outcome as well as any conditions the Identity Provider
        has specified. ALL of the conditions must be met in order for the response to be considered
        valid. If any of the conditions is not met or unknown, the response must be rejected.

        Also verify that the ID of the response is known, i.e. matches one of the IDs of the
        authentication requests we made, otherwise the response must be rejected.

        See also:
            http://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf

        Args:
            response: The SAML response (XML) received from the Identity Provider

        Returns:
            Authenticated: The authentication was successful and all of the conditions were met

        Raises:
            AttributeError: The User ID attribute is missing
            AttributeError: The algorithm used to sign the response is deemed insecure

            pysaml2 Exceptions:
                ToEarly: The authentication request response is not yet valid
                ResponseLifetimeExceed: The authentication request response has expired
                Exception: The response is intended for a different audience, or the
                    condition is unknown or not well-formed
               ...
        """
        # TODO (CMK-11851): One of the reasons why this could fail is that the metadata of the IdP
        # changed. Isolate the resulting error(s), refresh the config and retry.

        LOGGER.debug("Parsing authentication request response")

        # If the authentication failed, e.g. due to some failed conditions, the pysaml2 client will
        # raise an Exception. The type of the Exception is highly inconsistent (see function
        # docstring).
        authentication_response = self._client.parse_authn_request_response(
            saml_response, BINDING_HTTP_POST
        )
        if any(
            (
                authentication_response.response.signature.signed_info.signature_method.algorithm
                not in self._allowed_algorithms,
                authentication_response.assertion.signature.signed_info.signature_method.algorithm
                not in self._allowed_algorithms,
            )
        ):
            LOGGER.debug(
                "Rejecting authentication attempt based on insecure algorithm used to sign the response/assertion"
            )
            raise AttributeError("Insecure algorithm used for signature")

        self.validate_in_response_to_id(authentication_response)

        LOGGER.debug("Found user attributes: %s", ", ".join(authentication_response.ava.keys()))

        LOGGER.debug("Mapping User ID to field %s", self._user_id_attribute)
        if not (user_id := authentication_response.ava.get(self._user_id_attribute)):
            LOGGER.debug("User ID not found or empty, value is: %s", repr(user_id))
            raise AttributeError("User ID not found or empty")

        return Authenticated(
            in_response_to_id=RequestId(authentication_response.session_id()),
            user_id=UserId(user_id[0]),
            # TODO (CMK-11868): also grab other attributes, e.g. email, ...
        )

    def validate_in_response_to_id(self, authentication_response: AuthnResponse) -> None:
        """Validate authentication request response IDs.

        Each authentication request response contains the field "InResponseTo", which holds the ID
        of the original authentication request that was sent by the service provider. These IDs
        should be known IDs, otherwise the response is to a request that has never been made.

        We would normally delegate this to the client, however, the UserConnectors only live on a
        per-session basis. Since the full authentication cycle is technically two sessions (see
        pages saml_sso.py/saml_acs.py), the authentication request IDs are stored in Redis and
        validated here.

        Once the request response ID has been read from Redis, it is deleted, as it does not need to be
        stored for later processing. This follows the principle of the 'OneTimeUse' condition the
        Identity Provider may have specified regarding the validity of the response.

        See also:
            http://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf

        Args:
            authentication_response: The unmodified authentication response object returned by the
                pysaml2 client

        Returns:
            None: The validation was successful and the response is valid

        Raises:
            AttributeError: The validation was unsuccessful and the response must be rejected
        """
        if not authentication_response.in_response_to:
            LOGGER.debug(
                "Got authentication request response with missing InResponseTo ID from entity %s",
                authentication_response.issuer(),
            )
            raise AttributeError("Missing InResponseTo ID")

        if not authentication_response.check_subject_confirmation_in_response_to(
            authentication_response.in_response_to
        ):
            # The Identity Provider can send multiple assertion statements within the authentication
            # request response. All of these must be in response to the original authentication
            # request, otherwise the response must be rejected.
            LOGGER.warning(
                "Got unsolicited response from entity %s", authentication_response.issuer()
            )
            raise AttributeError("Inconsistent InResponseTo ID found in attribute statements")

        in_response_to_id = authentication_response.in_response_to
        if not (
            identity_provider_entity_id := query_redis(
                client=AUTHORIZATION_REQUEST_ID_DATABASE,
                data_key=self._redis_namespace,
                integrity_callback=lambda: IntegrityCheckResponse.USE,
                update_callback=lambda p: None,
                query_callback=lambda: AUTHORIZATION_REQUEST_ID_DATABASE.getdel(
                    f"{self._redis_namespace}:{in_response_to_id}"
                ),
                timeout=5,
            )
        ):
            LOGGER.warning(
                "Got unsolicited response from entity %s: %s",
                authentication_response.issuer(),
                authentication_response.in_response_to,
            )
            raise AttributeError("Unknown or expired InResponseTo ID")

        if identity_provider_entity_id != authentication_response.issuer():
            LOGGER.warning(
                "Got unexpected response from entity %s, expected %s",
                authentication_response.issuer(),
                identity_provider_entity_id,
            )
            raise AttributeError("Response from unexpected entity")
