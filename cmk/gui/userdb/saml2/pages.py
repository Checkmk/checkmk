#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client as http_client
from datetime import datetime
from typing import NamedTuple

from cmk.utils.redis import get_redis_client

from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.pages import Page, PageRegistry
from cmk.gui.plugins.userdb.utils import get_connection
from cmk.gui.session import session
from cmk.gui.userdb.saml2.connector import Connector
from cmk.gui.userdb.saml2.interface import HTTPPostRequest, Interface, XMLData
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

    def page(self) -> XMLData:
        connector, _relay_state = _initialise_page(
            request_method=request.request_method,
            allowed_method="GET",
            relay_state_string=request.get_ascii_input_mandatory("RelayState"),
        )

        interface = Interface(connector.config.interface_config, get_redis_client())
        return interface.metadata

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

    def page(self) -> HTTPPostRequest:
        relay_state_string = request.get_ascii_input_mandatory("RelayState")

        connector, relay_state = _initialise_page(
            request_method=request.request_method,
            allowed_method="GET",
            relay_state_string=relay_state_string,
        )

        # NOTE: more than one IdP connection is possible. If more IdPs should be supported in the
        # future, the connection_id parameter would enable us to decide which one the user has chosen.
        LOGGER.debug(
            "Authentication request to Identity Provider %s at URL %s",
            relay_state.connection_id,
            connector.config.identity_provider_url,
        )
        LOGGER.debug("Authentication request with RelayState=%s", relay_state_string)

        try:
            interface = Interface(connector.config.interface_config, get_redis_client())
            authentication_request = interface.authentication_request(relay_state.target_url)
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.warning(
                "%s - %s: %s",
                connector.config.identity_provider_url,
                type(e).__name__,
                str(e),
            )
            raise MKUserError(
                varname=None, message=_("Unable to create authentication request")
            ) from e

        return authentication_request

    def handle_page(self) -> None:
        try:
            # The client (user) receives a response which is actually a request it forwards to the
            # Identity Provider. This is a HTML form that gets automatically submitted to the
            # Identity Provider (POST method).
            post_request = self.page()
            response.headers.extend(post_request.headers)
            response.set_data(post_request.data)
        except Exception as e:  # pylint: disable=broad-except
            page_exception_handler(
                exception=e, relay_state_string=request.get_ascii_input_mandatory("RelayState")
            )


class AssertionConsumerService(Page):
    """Consume authentication request responses received from the Identity Provider.

    Authentication requests are made by the SingleSignOn page.
    """

    def page(self) -> None:
        connector, relay_state = _initialise_page(
            request_method=request.request_method,
            allowed_method="POST",
            relay_state_string=request.get_ascii_input_mandatory("RelayState"),
        )

        LOGGER.debug(
            "Authentication request response from Identity Provider %s at URL %s",
            relay_state.connection_id,
            connector.config.identity_provider_url,
        )

        if not (saml_response := request.form.get("SAMLResponse")):
            raise MKUserError(varname=None, message=_("Got no response from IdP"))

        try:
            interface = Interface(connector.config.interface_config, get_redis_client())
            authn_response = interface.parse_authentication_request_response(
                saml_response=saml_response
            )
        except Exception as e:  # pylint: disable=broad-except
            # This most likely means that some conditions the Identity Provider has specified were
            # not met. Note that the type of the exception raised by the client may be a bare
            # Exception.
            LOGGER.warning(
                "%s - %s: %s",
                connector.config.identity_provider_url,
                type(e).__name__,
                str(e),
            )
            raise MKUserError(message=_("Authentication failed"), varname=None) from e

        try:
            connector.create_and_update_user(authn_response.user_id, authn_response)
        except ValueError as e:
            LOGGER.warning("%s: %s", type(e).__name__, str(e))
            raise MKUserError(message=_("Unknown user"), varname=None) from e

        on_succeeded_login(authn_response.user_id, datetime.now())

        session.user = LoggedInUser(authn_response.user_id)

        # self.connector.update_user(authn_response.user_id)
        raise HTTPRedirect(relay_state.target_url)

    def handle_page(self) -> None:
        try:
            self.page()
        except Exception as e:  # pylint: disable=broad-except
            page_exception_handler(
                exception=e, relay_state_string=request.get_ascii_input_mandatory("RelayState")
            )


def _initialise_page(
    request_method: str, allowed_method: str, relay_state_string: str
) -> tuple[Connector, RelayState]:
    if request_method != allowed_method:
        raise MKUserError(varname=None, message=_("Method not allowed"))

    relay_state = _relay_state_from_url(relay_state_string)

    connector = _connector(relay_state.connection_id)

    if not connector.is_enabled():
        LOGGER.debug("Connection for ID %s is currently disabled", relay_state.connection_id)
        raise MKUserError(
            varname=None,
            message=_(
                "This connection is currently disabled. Please contact your system administrator."
            ),
        )

    return connector, relay_state


def page_exception_handler(exception: Exception, relay_state_string: str) -> None:
    relay_state = _relay_state_from_url(relay_state_string)

    if isinstance(exception, HTTPRedirect):
        raise exception

    if isinstance(exception, MKUserError):
        LOGGER.debug(exception, exc_info=True)
        raise _redirect_to_login_with_error(
            origtarget=relay_state.target_url, error_message=str(exception)
        )

    # Messages of exceptions may contain sensitive information that the user should not
    # see in the front-end. We only show messages in the GUI if they stem from
    # 'MKUserError' exception types.
    LOGGER.exception(exception)
    raise _redirect_to_login_with_error(
        origtarget=relay_state.target_url,
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
