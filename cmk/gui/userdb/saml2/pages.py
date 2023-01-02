#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client as http_client
from datetime import datetime
from typing import NamedTuple

from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.pages import Page, PageRegistry
from cmk.gui.plugins.userdb.utils import get_connection
from cmk.gui.session import session
from cmk.gui.userdb.saml2.connector import Connector
from cmk.gui.userdb.saml2.interface import Interface, XMLData
from cmk.gui.userdb.session import on_succeeded_login
from cmk.gui.utils import is_allowed_url
from cmk.gui.utils.urls import makeuri_contextless

LOGGER = logger.getChild("saml2")


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
        LOGGER.debug("The parameter %s is not a valid URL", url)
        raise MKUserError(varname=None, message=_("URL not allowed"))

    return RelayState(target_url=url, connection_id=id_)


def _connector(connection_id: str) -> Connector:
    LOGGER.debug("Accessing SAML2.0 connector")
    connector = get_connection(connection_id)
    assert isinstance(connector, Connector)
    return connector


class Metadata(Page):
    """Metadata information the Checkmk server provides on itself.

    The Identity Provider requests this service to validate that it is dealing with a known entity.
    """

    @property
    def relay_state(self) -> RelayState:
        return _relay_state_from_url(request.get_ascii_input_mandatory("RelayState"))

    @property
    def connector(self) -> Connector:
        return _connector(self.relay_state.connection_id)

    def page(self) -> XMLData:
        if not self.connector.is_enabled():
            LOGGER.debug(
                "Requested metadata for connection %s at URL %s but is currently disabled",
                (self.relay_state.connection_id, self.connector.identity_provider_url),
            )
            raise MKUserError(
                varname=None,
                message=_(
                    "This connection is currently disabled. Please contact your system administrator."
                ),
            )

        return self.connector.interface.metadata

    def handle_page(self) -> None:
        try:
            response.set_content_type("application/xml")
            response.set_data(self.page().encode("utf-8"))
        except MKUserError as e:
            LOGGER.debug(e, exc_info=True)
            response.status_code = http_client.SERVICE_UNAVAILABLE
            response.set_data(str(e))
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.exception(e)
            response.set_content_type("text/plain")
            response.status_code = http_client.INTERNAL_SERVER_ERROR
            response.set_data(_("Unable to process request"))


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
            raise MKUserError(varname=None, message=_("Method not allowed"))

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
            raise MKUserError(
                varname=None,
                message=_(
                    "This connection is currently disabled. Please contact your system administrator."
                ),
            )

        LOGGER.debug("Authentication request with RelayState=%s", self.relay_state_string)

        try:
            authentication_request = self.connector.interface.authentication_request(
                self.relay_state_string
            )
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.warning(
                "%s - %s: %s", self.connector.identity_provider_url(), type(e).__name__, str(e)
            )
            raise MKUserError(
                varname=None, message=_("Unable to create authentication request")
            ) from e

        LOGGER.debug("Authentication request to URL: %s", authentication_request)

        raise HTTPRedirect(authentication_request)

    def handle_page(self) -> None:
        try:
            self.page()
        except HTTPRedirect:
            raise
        except MKUserError as e:
            LOGGER.debug(e, exc_info=True)
            raise _redirect_to_login_with_error(
                origtarget=self.relay_state.target_url, error_message=str(e)
            )
        except Exception as e:  # pylint: disable=broad-except
            # Messages of exceptions may contain sensitive information that the user should not
            # see in the front-end. We only show messages in the GUI if they stem from
            # 'MKUserError' exception types.
            LOGGER.exception(e)
            raise _redirect_to_login_with_error(
                origtarget=self.relay_state.target_url,
                error_message=_("Unhandled exception occurred"),
            )


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
            raise MKUserError(varname=None, message=_("Method not allowed"))

        LOGGER.debug(
            "Authentication request response from Identity Provider %s at URL %s",
            (self.relay_state.connection_id, self.connector.identity_provider_url),
        )

        if not self.connector.is_enabled():
            LOGGER.debug(
                "Connection for ID %s is currently disabled", self.relay_state.connection_id
            )
            raise MKUserError(
                varname=None,
                message=_(
                    "This connection is currently disabled. Please contact your system administrator."
                ),
            )

        if not (saml_response := request.form.get("SAMLResponse")):
            raise MKUserError(varname=None, message=_("Got no response from IdP"))

        try:
            authn_response = self.connector.interface.parse_authentication_request_response(
                saml_response=saml_response
            )
        except Exception as e:  # pylint: disable=broad-except
            # This most likely means that some conditions the Identity Provider has specified were
            # not met. Note that the type of the exception raised by the client may be a bare
            # Exception.
            LOGGER.warning(
                "%s - %s: %s", self.connector.identity_provider_url(), type(e).__name__, str(e)
            )
            raise MKUserError(message=_("Authentication failed"), varname=None) from e

        try:
            self.connector.create_and_update_user(authn_response.user_id)
        except ValueError as e:
            LOGGER.warning("%s: %s", type(e).__name__, str(e))
            raise MKUserError(message=_("Unknown user"), varname=None) from e

        on_succeeded_login(authn_response.user_id, datetime.now())

        session.user = LoggedInUser(authn_response.user_id)

        # self.connector.update_user(authn_response.user_id)
        raise HTTPRedirect(self.relay_state.target_url)

    def handle_page(self) -> None:
        try:
            self.page()
        except HTTPRedirect:
            raise
        except MKUserError as e:
            LOGGER.debug(e, exc_info=True)
            raise _redirect_to_login_with_error(
                origtarget=self.relay_state.target_url, error_message=str(e)
            )
        except Exception as e:  # pylint: disable=broad-except
            # Messages of exceptions may contain sensitive information that the user should not
            # see in the front-end. We only show messages in the GUI if they stem from
            # 'MKUserError' exception types.
            LOGGER.exception(e)
            raise _redirect_to_login_with_error(
                origtarget=self.relay_state.target_url,
                error_message=_("Unhandled exception occurred"),
            )


def _redirect_to_login_with_error(origtarget: str, error_message: str) -> HTTPRedirect:
    return HTTPRedirect(
        makeuri_contextless(
            request,
            [
                ("_origtarget", origtarget),
                ("_saml2_user_error", error_message),
            ],
            filename="login.py",
        )
    )


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page("noauth:saml_acs")(AssertionConsumerService)
    page_registry.register_page("noauth:saml_metadata")(Metadata)
    page_registry.register_page("noauth:saml_sso")(SingleSignOn)
