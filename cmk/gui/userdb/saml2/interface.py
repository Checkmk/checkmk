#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import NewType

import requests
from pydantic import BaseModel
from redis import Redis
from redis.client import Pipeline
from saml2.client import Saml2Client
from saml2.config import SPConfig
from saml2.metadata import create_metadata_string
from saml2.response import AuthnResponse
from saml2.s_utils import UnknownSystemEntity
from saml2.saml import NAMEID_FORMAT_PERSISTENT

from cmk.utils.redis import IntegrityCheckResponse, query_redis
from cmk.utils.type_defs import UserId

from cmk.gui.config import active_config
from cmk.gui.groups import load_contact_group_information
from cmk.gui.log import logger
from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb.saml2.config import (
    ConnectivitySettings,
    InterfaceConfig,
    SecuritySettings,
    URL,
    UserAttributeNames,
    XMLText,
)

LOGGER = logger.getChild("saml2")


HTMLFormString = NewType("HTMLFormString", str)
RequestId = NewType("RequestId", str)


class HTTPPostRequest(BaseModel):
    data: HTMLFormString
    headers: list[tuple[str, str]]


class AuthenticatedUser(BaseModel):
    user_id: UserId
    alias: str
    email: str | None
    force_authuser: bool
    contactgroups: Sequence[str]
    roles: Sequence[str]


def _metadata_from_idp(url: str, timeout: tuple[int, int]) -> str | None:
    # TODO (CMK-11851): IdP metadata changes rarely so the content should be cached.
    metadata = requests.get(url, verify=True, timeout=timeout)
    if metadata.status_code < 200 or metadata.status_code > 299:
        LOGGER.critical("Failed to fetch metadata from URL %s", url)
        return None
    return metadata.text


def saml_config(connection: ConnectivitySettings, security: SecuritySettings) -> SPConfig:
    """Convert valuespecs into a valid SAML Service Provider configuration."""
    config = SPConfig()
    sp_configuration = {
        "endpoints": {
            "assertion_consumer_service": [
                (connection.assertion_consumer_service_endpoint, connection.binding),
            ]
        },
        "allow_unsolicited": security.allow_unknown_user_attributes,
        "authn_requests_signed": security.sign_authentication_requests,
        "want_assertions_signed": security.enforce_signed_assertions,
        "want_response_signed": security.enforce_signed_responses,
        "signing_algorithm": security.signing_algortithm,
        "digest_algorithm": security.digest_algorithm,  # this is referring to the digest alg the counterparty should use
    }

    if isinstance(connection.idp_metadata, URL):
        idp_metadata = {
            "remote": [
                {
                    "url": str(connection.idp_metadata),
                }
            ]
        }
    else:
        # The below suppression is due to a bug with the types-pysaml2 package
        idp_metadata = {"inline": [str(connection.idp_metadata)]}  # type: ignore

    config.load(
        {
            "entityid": connection.entity_id,
            "metadata": idp_metadata,
            "service": {"sp": sp_configuration},
            "allow_unknown_attributes": security.allow_unknown_user_attributes,
            "http_client_timeout": connection.timeout,
            "key_file": str(security.signature_certificate.private),
            "cert_file": str(security.signature_certificate.public),
            "encryption_keypairs": [
                {
                    # TODO (CMK-11946): implement encryption
                    "key_file": "",
                    "cert_file": "",
                },
            ],
            "attribute_map_dir": str(
                security.user_attribute_mappings_dir
            ),  # See README in this directory for more information on this option
            "verify_ssl_cert": connection.verify_tls,
        }
    )
    return config


class Interface:
    def __init__(self, config: InterfaceConfig, requests_db: Redis[str]) -> None:
        self._config = saml_config(
            connection=config.connectivity_settings, security=config.security_settings
        )
        self._user_attribute_names = config.user_attributes.attribute_names
        self._role_membership_mapping = config.user_attributes.role_membership_mapping

        if self._config.metadata is None:
            raise AttributeError("Got no metadata information from Identity Provider")

        self._identity_provider_entity_id = list(self._config.metadata.keys())[
            0
        ]  # May or may not be the metadata endpoint of the IdP

        self.acs_endpoint = config.connectivity_settings.assertion_consumer_service_endpoint
        self.acs_binding = config.connectivity_settings.binding

        self._client = Saml2Client(config=self._config)
        try:
            self.idp_sso_binding, self.idp_sso_destination = self._client.pick_binding(
                "single_sign_on_service",
                [self.acs_binding],
                "idpsso",
                entity_id=self._identity_provider_entity_id,
            )
        except UnknownSystemEntity:
            # TODO (CMK-11846): handle this
            raise UnknownSystemEntity

        self._metadata = create_metadata_string(configfile=None, config=self._config).decode(
            "utf-8"
        )

        # Maintaining an allow-list has the advantage of knowing exactly what we support, and we are
        # less prone to changes made to the pysaml2 dependency. New algorithms are not added
        # frequently.
        self._allowed_algorithms = config.security_settings.allowed_algorithms

        self._redis_requests_db = requests_db
        self._redis_namespace = config.cache_settings.redis_namespace
        self._authentication_request_id_expiry = (
            config.cache_settings.authentication_request_id_expiry
        )

    @property
    def metadata(self) -> XMLText:
        """Entity ID that is registered with the Identity Provider and information about preferred
        bindings.

        Returns:
            A valid XML string
        """
        return XMLText(self._metadata)

    def authentication_request(self, relay_state: str) -> HTTPPostRequest:
        """Authentication request to be forwarded to the Identity Provider.

        It is up to the Identity Provider to perform any authentication if the user is not already
        logged in.

        Additionally, the request IDs are tracked so that it can be verified that responses received
        are in response to a request that has actually been made.

        A HTTP POST binding is used to send the requests. This means that the data is represented as
        an HTML form, which gets automatically submitted once the client (user's browser) receives
        it.

        The alternative binding is HTTP Redirect, however, this means that the SAML request is
        included as a HTTP parameter, which is limited in size. This size is easily exceeded when
        the signature certificate is included (as per the SAML specification).

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
                self._authentication_request_id_expiry,
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
            client=self._redis_requests_db,
            data_key=self._redis_namespace,
            integrity_callback=lambda: IntegrityCheckResponse.UPDATE,
            update_callback=_redis_update_query,
            query_callback=lambda: None,
            timeout=5,
        )

        http_request_params = self._client.apply_binding(
            self.idp_sso_binding,
            authn_request,
            self.idp_sso_destination,
            relay_state=relay_state,
        )

        LOGGER.debug("HTTP request: %s", repr(http_request_params))
        return HTTPPostRequest(
            data=HTMLFormString(http_request_params["data"]), headers=http_request_params["headers"]
        )

    def parse_authentication_request_response(self, saml_response: str) -> AuthenticatedUser:
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
            saml_response, self.acs_binding
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

        LOGGER.debug("Mapping User ID to field %s", self._user_attribute_names.user_id)
        if not (user_id := authentication_response.ava.get(self._user_attribute_names.user_id)):
            LOGGER.debug("User ID not found or empty, value is: %s", repr(user_id))
            raise AttributeError("User ID not found or empty")

        return user_attributes_to_authenticated_user(
            user_attribute_names=self._user_attribute_names,
            user_id=UserId(user_id[0]),
            user_attributes=authentication_response.ava,
            default_user_profile=active_config.default_user_profile,
            checkmk_contact_groups=set(load_contact_group_information()),
            roles_mapping=self._role_membership_mapping,
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
                client=self._redis_requests_db,
                data_key=self._redis_namespace,
                integrity_callback=lambda: IntegrityCheckResponse.USE,
                update_callback=lambda p: None,
                query_callback=lambda: self._redis_requests_db.getdel(
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


def user_attributes_to_authenticated_user(
    user_attribute_names: UserAttributeNames,
    user_id: UserId,
    user_attributes: Mapping[str, Sequence[str]],
    default_user_profile: UserSpec,
    checkmk_contact_groups: set[str],
    roles_mapping: Mapping[str, set[str]],
) -> AuthenticatedUser:
    """Map user attributes from the authentication request response to Checkmk user attributes.

    The mapping can be configured via the Setup configuration page.

    Some fields are optional (denoted with 'None'). If that is the case, the default profile is used
    that can be configured via the global settings.

    Args:
        user_attribute_names: a string representing the field name of the SAML attribute, or 'None'
            if no mapping is configured
        user_id: the user ID value of the user
        user_attributes: a dictionary containing the SAML attributes the Identity Provider has sent
            for the user
        default_user_profile: default attributes that should be assigned to new users if no explicit
            mapping has been configured

    Returns:
        An 'AuthenticatedUser' instance that can be used to write information to the 'UserStore'
    """

    alias = str(user_id)
    if user_attribute_names.alias:
        alias = user_attributes.get(user_attribute_names.alias, [str(user_id)])[0]

    email = None
    if user_attribute_names.email and (
        email_attribute := user_attributes.get(user_attribute_names.email)
    ):
        email = email_attribute[0]

    contactgroups = default_user_profile["contactgroups"]
    if user_attribute_names.contactgroups:
        contactgroups = list(
            set(user_attributes.get(user_attribute_names.contactgroups, []))
            & checkmk_contact_groups
        )

    roles = default_user_profile["roles"]
    if user_attribute_names.roles is not None:
        roles = list(
            _external_to_checkmk_memberships(
                set(user_attributes.get(user_attribute_names.roles, [])), roles_mapping
            )
        )

    return AuthenticatedUser(
        user_id=user_id,
        alias=alias,
        email=email,
        contactgroups=contactgroups,
        force_authuser=default_user_profile["force_authuser"],
        roles=roles,
    )


def _external_to_checkmk_memberships(
    external_memberships: set[str], memberships_mapping: Mapping[str, set[str]]
) -> Iterable[str]:
    """

    >>> list(_external_to_checkmk_memberships({"admin", "superduperadmin", "normal_user"},
    ... {"admin": {"superduperadmin"}, "user": {"normal_user"}}))
    ['admin', 'user']

    >>> list(_external_to_checkmk_memberships({"normal_user"},
    ... {"admin": {"superduperadmin"}, "user": {"normal_user"}}))
    ['user']

    """
    if not external_memberships:
        return

    for checkmk_membership, corresponding_memberships in memberships_mapping.items():
        if external_memberships & corresponding_memberships:
            yield checkmk_membership
