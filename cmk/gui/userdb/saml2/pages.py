#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import http.client as http_client
from datetime import datetime

from cmk.gui.crash_handler import handle_exception_as_gui_crash_report
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKGeneralException
from cmk.gui.http import request, response
from cmk.gui.log import logger
from cmk.gui.pages import Page, PageRegistry
from cmk.gui.plugins.userdb.utils import get_connection
from cmk.gui.userdb.saml2.connector import Connector, SAML2_CONNECTOR_TYPE
from cmk.gui.userdb.saml2.interface import Interface, NotAuthenticated, XMLData
from cmk.gui.userdb.session import create_auth_session, on_succeeded_login

LOGGER = logger.getChild("saml2")


class MKSaml2Exception(MKGeneralException):
    pass


def _interface() -> Interface:
    LOGGER.debug("Accessing SAML2.0 connector")
    connector = get_connection(SAML2_CONNECTOR_TYPE)
    assert isinstance(connector, Connector)
    return connector.interface


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
    def _interface(self) -> Interface:
        return _interface()

    def page(self) -> XMLData:
        return self._interface.metadata


class SingleSignOn(Page):
    """Send authentication requests to the Identity Provider.

    The implementation detail of the authentication is up to the Identity Provider and may include
    any form of authentication method as well as a combination of multiple authentication methods.

    Responses to authentication requests are sent to a different endpoint: AssertionConsumerService.
    """

    @property
    def _interface(self) -> Interface:
        return _interface()

    def page(self) -> None:
        # NOTE: more than one IdP connection is possible
        if request.request_method != "GET":
            raise MKSaml2Exception(f"Method {request.request_method} not allowed")

        relay_state = request.get_url_input("RelayState")
        LOGGER.debug("Authentication request with RelayState=%s", relay_state)

        if (authentication_request := self._interface.authentication_request(relay_state)) is None:
            raise MKSaml2Exception("Unable to create authentication request")

        LOGGER.debug("Authentication request to URL: %s", authentication_request)

        raise HTTPRedirect(authentication_request)


class AssertionConsumerService(Page):
    """Consume authentication request responses received from the Identity Provider.

    Authentication requests are made by the SingleSignOn page.
    """

    @property
    def _interface(self) -> Interface:
        return _interface()

    def page(self) -> None:
        if request.request_method != "POST":
            raise MKSaml2Exception(f"Method {request.request_method} not allowed")

        if not (saml_response := request.form.get("SAMLResponse")):
            raise MKSaml2Exception("Got no response from IdP")

        authn_response = self._interface.parse_authentication_request_response(
            saml_response=saml_response,
            relay_state=request.get_url_input(
                "RelayState"
            ),  # make sure RelayState is an allowed URL
        )

        if isinstance(authn_response, NotAuthenticated):
            raise MKAuthException("Invalid login")

        # TODO (CMK-11849): The current assumption is that the user already exists in Checkmk. If that's
        # not the case, the user should be created ad-hoc. When it is created, we need to be careful
        # not to overlap with users that may exist locally.

        # TODO (CMK-11849): The permission group the user belongs to, along with other attributes, could
        # change. This should be updated too.
        session_id = on_succeeded_login(authn_response.user_id, datetime.now())

        # TODO (CMK-11846): If for whatever reason the session is not created successfully, a message
        # should be displayed after the redirect to the login page.
        create_auth_session(authn_response.user_id, session_id)

        raise HTTPRedirect(authn_response.relay_state)


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page("noauth:saml_acs")(AssertionConsumerService)
    page_registry.register_page("noauth:saml_metadata")(Metadata)
    page_registry.register_page("noauth:saml_sso")(SingleSignOn)
