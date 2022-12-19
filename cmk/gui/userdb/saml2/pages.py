#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import http.client as http_client
from datetime import datetime
from typing import NamedTuple

from cmk.gui.crash_handler import handle_exception_as_gui_crash_report
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKGeneralException
from cmk.gui.http import request, response
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.pages import Page, PageRegistry
from cmk.gui.plugins.userdb.utils import get_connection
from cmk.gui.session import session
from cmk.gui.userdb.saml2.connector import Connector
from cmk.gui.userdb.saml2.interface import Interface, NotAuthenticated, XMLData
from cmk.gui.userdb.session import on_succeeded_login
from cmk.gui.utils import is_allowed_url

LOGGER = logger.getChild("saml2")


class MKSaml2Exception(MKGeneralException):
    pass


class RelayState(NamedTuple):
    target_url: str
    connection_id: str

    def __str__(self) -> str:
        return f"{self.connection_id},{self.target_url}"


def _relay_state_from_url(relay_state: str) -> RelayState:
    """
    >>> _relay_state_from_url("123-456,index.py")
    RelayState(target_url='index.py', connection_id='123-456')

    >>> _relay_state_from_url("123-456,index.py?so=many,many,many,params")
    RelayState(target_url='index.py?so=many,many,many,params', connection_id='123-456')
    """

    id_, url = relay_state.split(",", 1)

    if not is_allowed_url(url):
        # TODO (CMK-11846): handle this, so that it is shown nicely in the GUI
        raise ValueError(f"The parameter {url} is not a valid URL")

    return RelayState(target_url=url, connection_id=id_)


def _connector(connection_id: str) -> Connector:
    LOGGER.debug("Accessing SAML2.0 connector")
    connector = get_connection(connection_id)
    assert isinstance(connector, Connector)
    return connector


class XMLPage(Page, abc.ABC):
    def handle_page(self) -> None:
        try:
            response.set_content_type("application/xml")
            response.set_data(self.page().encode("utf-8"))
        except MKGeneralException as e:
            response.set_content_type("text/plain")
            response.status_code = http_client.BAD_REQUEST
            response.set_data(str(e))
        except Exception as e:
            response.set_content_type("text/plain")
            response.status_code = http_client.INTERNAL_SERVER_ERROR
            handle_exception_as_gui_crash_report(
                plain_error=True,
                show_crash_link=getattr(g, "may_see_crash_reports", False),
            )
            response.set_data(str(e))

    @abc.abstractmethod
    def page(self):
        """Override this to implement the page functionality"""
        raise NotImplementedError()


class Metadata(XMLPage):
    """Metadata information the Checkmk server provides on itself.

    The Identity Provider requests this service to validate that it is dealing with a known entity.
    """

    @property
    def relay_state(self) -> RelayState:
        return _relay_state_from_url(request.get_ascii_input_mandatory("RelayState"))

    @property
    def connector(self) -> Connector:
        return _connector(self.relay_state.connection_id)

    def page(self) -> XMLData | None:
        if not self.connector.is_enabled():
            LOGGER.debug(
                "Requested metadata for connection %s at URL %s but is currently disabled",
                (self.relay_state.connection_id, self.connector.identity_provider_url),
            )
            # TODO (CMK-11846): handle this
            return None
        return self.connector.interface.metadata


class SingleSignOn(Page):
    """Send authentication requests to the Identity Provider.

    The implementation detail of the authentication is up to the Identity Provider and may include
    any form of authentication method as well as a combination of multiple authentication methods.

    Responses to authentication requests are sent to a different endpoint: AssertionConsumerService.
    """

    @property
    def relay_state_string(self) -> str:
        return request.get_ascii_input_mandatory("RelayState")

    @property
    def relay_state(self) -> RelayState:
        return _relay_state_from_url(self.relay_state_string)

    @property
    def connector(self) -> Connector:
        return _connector(self.relay_state.connection_id)

    @property
    def interface(self) -> Interface:
        return self.connector.interface

    def page(self) -> None:
        if request.request_method != "GET":
            raise MKSaml2Exception(f"Method {request.request_method} not allowed")

        # NOTE: more than one IdP connection is possible. If more IdPs should be supported in the
        # future, the connection_id parameter would enable us to decide which one the user has chosen.
        LOGGER.debug(
            "Authentication request to Identity Provider %s at URL %s",
            (self.relay_state.connection_id, self.connector.identity_provider_url),
        )

        if not self.connector.is_enabled():
            LOGGER.debug(
                "Connection for ID %s is currently disabled", self.relay_state.connection_id
            )
            # TODO (CMK-11846): handle this
            return

        LOGGER.debug("Authentication request with RelayState=%s", self.relay_state_string)

        if (
            authentication_request := self.connector.interface.authentication_request(
                self.relay_state_string
            )
        ) is None:
            raise MKSaml2Exception("Unable to create authentication request")

        LOGGER.debug("Authentication request to URL: %s", authentication_request)

        raise HTTPRedirect(authentication_request)


class AssertionConsumerService(Page):
    """Consume authentication request responses received from the Identity Provider.

    Authentication requests are made by the SingleSignOn page.
    """

    @property
    def relay_state(self) -> RelayState:
        return _relay_state_from_url(request.get_ascii_input_mandatory("RelayState"))

    @property
    def connector(self) -> Connector:
        return _connector(self.relay_state.connection_id)

    def page(self) -> None:
        if request.request_method != "POST":
            raise MKSaml2Exception(f"Method {request.request_method} not allowed")

        LOGGER.debug(
            "Authentication request response from Identity Provider %s at URL %s",
            (self.relay_state.connection_id, self.connector.identity_provider_url),
        )

        if not self.connector.is_enabled():
            LOGGER.debug(
                "Connection for ID %s is currently disabled", self.relay_state.connection_id
            )
            # TODO (CMK-11846): handle this
            return

        if not (saml_response := request.form.get("SAMLResponse")):
            raise MKSaml2Exception("Got no response from IdP")

        authn_response = self.connector.interface.parse_authentication_request_response(
            saml_response=saml_response
        )

        if isinstance(authn_response, NotAuthenticated):
            raise MKAuthException("Invalid login")

        # TODO (CMK-11849): The current assumption is that the user already exists in Checkmk. If that's
        # not the case, the user should be created ad-hoc. When it is created, we need to be careful
        # not to overlap with users that may exist locally.

        # TODO (CMK-11849): The permission group the user belongs to, along with other attributes, could
        # change. This should be updated too.
        on_succeeded_login(authn_response.user_id, datetime.now())

        # TODO (CMK-11846): If for whatever reason the session is not created successfully, a message
        # should be displayed after the redirect to the login page.
        session.user = LoggedInUser(authn_response.user_id)

        raise HTTPRedirect(self.relay_state.target_url)


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page("noauth:saml_acs")(AssertionConsumerService)
    page_registry.register_page("noauth:saml_metadata")(Metadata)
    page_registry.register_page("noauth:saml_sso")(SingleSignOn)
