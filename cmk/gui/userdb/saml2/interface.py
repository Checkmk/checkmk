#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, NamedTuple, NewType

import requests
from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.client import Saml2Client
from saml2.config import SPConfig
from saml2.metadata import create_metadata_string
from saml2.s_utils import UnknownSystemEntity
from saml2.saml import NAMEID_FORMAT_PERSISTENT

from cmk.utils.site import url_prefix
from cmk.utils.type_defs import UserId

from cmk.gui.log import logger

# TODO (CMK-11846): currently this logs to cmk.web.saml2 but it would be good to have dedicated logging
# for SAML that can be changed via the global settings
LOGGER = logger.getChild("saml2")

XMLData = NewType("XMLData", str)
URLRedirect = NewType("URLRedirect", str)
RequestId = NewType("RequestId", str)


class Authenticated(NamedTuple):
    user_id: UserId
    in_response_to_id: RequestId


class NotAuthenticated(NamedTuple):
    reason: str


AuthenticationRequestResponse = Authenticated | NotAuthenticated


def _metadata_from_idp(url: str, timeout: tuple[int, int]) -> str | None:
    # TODO (CMK-11851): IdP metadata changes rarely so the content should be cached.
    metadata = requests.get(url, verify=True, timeout=timeout)
    if metadata.status_code < 200 or metadata.status_code > 299:
        # TODO (CMK-11846): this should be logged appropriately
        return None
    return metadata.text


def raw_config_to_saml_config(raw_config: dict[str, Any]) -> SPConfig:
    """Convert valuespecs into a valid SAML Service Provider configuration."""
    config = SPConfig()
    timeout = raw_config["connection_timeout"]
    checkmk_base_url = f"{raw_config['checkmk_server_url']}{url_prefix()}check_mk"
    acs_endpoint_url = f"{checkmk_base_url}/saml_acs.py?acs"
    sp_configuration = {
        "endpoints": {
            "assertion_consumer_service": [
                (acs_endpoint_url, BINDING_HTTP_REDIRECT),
                (acs_endpoint_url, BINDING_HTTP_POST),
            ]
        },
        "allow_unsolicited": True,
        "authn_request_signed": False,
        "logout_requests_signed": False,
        "want_assertions_signed": False,
        "want_response_signed": False,
    }
    config.load(
        {
            "entityid": f"{checkmk_base_url}/saml_metadata.py",
            "metadata": {
                "inline": [_metadata_from_idp(raw_config["idp_metadata_endpoint"], timeout)]
            },
            "service": {"sp": sp_configuration},
            "allow_unknown_attributes": True,
            "http_client_timeout": timeout,
        }
    )
    return config


def raw_config_to_attributes_mapping(raw_config: dict[str, Any]) -> Mapping[str, str]:
    """Map attribute fields the Identity Provider sends to fields we expect."""
    assert isinstance(raw_config, dict)
    return {"user_id_attribute": raw_config["user_id_attribute"]}


class Interface:
    def __init__(self, raw_config: dict[str, Any]) -> None:
        self.__config = raw_config_to_saml_config(raw_config)
        self.__attributes_mapping = raw_config_to_attributes_mapping(raw_config)
        self.__user_id_attribute = self.__attributes_mapping["user_id_attribute"]
        self.__client = Saml2Client(config=self.__config)
        self.__metadata = create_metadata_string(configfile=None, config=self.__config).decode(
            "utf-8"
        )

        self.acs_endpoint, self.acs_binding = self.__config.getattr("endpoints")[
            "assertion_consumer_service"
        ]

        if self.__config.metadata is None:
            # TODO (CMK-11846): implement a more consistent way of logging errors
            raise AssertionError("Got no metadata information from Identity Provider")
        try:
            self.idp_sso_binding, self.idp_sso_destination = self.__client.pick_binding(
                "single_sign_on_service",
                [BINDING_HTTP_REDIRECT, BINDING_HTTP_POST],
                "idpsso",
                entity_id=list(self.__config.metadata.keys())[0],
            )
        except UnknownSystemEntity:
            # TODO (CMK-11846): handle this
            raise UnknownSystemEntity

    @property
    def metadata(self) -> XMLData:
        """Entity ID that is registered with the Identity Provider and information about preferred
        bindings.

        Returns:
            A valid XML string
        """
        return XMLData(self.__metadata)

    def authentication_request(self, relay_state: str) -> URLRedirect | None:
        """Authentication request to be forwarded to the Identity Provider.

        It is up to the Identity Provider to perform any authentication if the user is not already
        logged in.

        Args:
            relay_state: The URL the user originally requested and any other state information

        Returns:
            The URL, including the authentication request, that redirects the user to their Identity
            Provider's Single Sign-On service, or None if the authentication request cannot be
            created.
        """

        # TODO (CMK-11848): We must keep track of the request IDs that we sent to the IdP (saml_sso
        # endpoint), and verify that the response is to one of those requests. If it is a random
        # response to a request we never made, we must reject it.
        LOGGER.debug("Prepare authentication request")
        _authn_request_id, authn_request = self.__client.create_authn_request(
            self.idp_sso_destination,
            binding=self.acs_binding,
            extensions=None,
            # TODO (lisa): find out what this option does
            nameid_format=NAMEID_FORMAT_PERSISTENT,
        )
        http_headers = self.__client.apply_binding(
            self.idp_sso_binding,
            authn_request,
            self.idp_sso_destination,
            relay_state=relay_state,
        )["headers"]

        if (url_redirect := dict(http_headers).get("Location")) is None:
            LOGGER.debug("Redirect URL: %s", url_redirect)
            return None

        return URLRedirect(url_redirect)

    def parse_authentication_request_response(
        self, saml_response: str
    ) -> AuthenticationRequestResponse:
        """Parse responses received from the Identity Provider to authentication requests we made.

        Take into account the authentication outcome as well as any conditions the Identity Provider
        has specified. ALL of the conditions must be met in order for the response to be considered
        valid. If any of the conditions is not met, the response must be rejected.

        Also verify that the ID of the response is known, i.e. matches one of the IDs of the
        authentication requests we made, otherwise the response must be rejected.

        See also:
            http://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf

        Args:
            response: The SAML response (XML) received from the Identity Provider

        Returns:
            Authenticated: If the authentication was successful and all of the conditions were met.
            NotAuthenticated: If the authentication was unsuccessful or at least one of the
                conditions was not met (in this order).
        """
        # TODO (CMK-11851): One of the reasons why this could fail is that the metadata of the IdP
        # changed. Isolate the resulting error(s), refresh the config and retry.

        LOGGER.debug("Parsing authentication request response")

        authentication_response = self.__client.parse_authn_request_response(
            saml_response, BINDING_HTTP_POST
        )

        if not authentication_response.authn_statement_ok():
            LOGGER.debug("Rejecting authentication attempt based on failed authentication")
            return NotAuthenticated(reason="Invalid login")

        if not authentication_response.condition_ok():
            # TODO (CMK-11850): inspect use cases; ensure that this is already taking care of the time
            # window the response is valid for. Also: see whether it is possible to get more
            # information for the debug log.
            LOGGER.debug("Rejecting authentication attempt based on failed condition(s)")
            return NotAuthenticated(reason="Failed condition(s)")

        LOGGER.debug("Found user attributes: %s", ", ".join(authentication_response.ava.keys()))

        LOGGER.debug("Mapping User ID to field %s", self.__user_id_attribute)
        if not (user_id := authentication_response.ava.get(self.__user_id_attribute)):
            LOGGER.debug("User ID not found or empty, value is: %s", repr(user_id))
            return NotAuthenticated(reason="User ID not found or empty")

        return Authenticated(
            in_response_to_id=RequestId(authentication_response.session_id()),
            user_id=UserId(user_id[0]),
            # TODO (CMK-11849): also grab other attributes, e.g. email, ...
        )
