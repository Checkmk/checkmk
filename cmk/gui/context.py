#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This is our home-grown version of flask.globals and flask.ctx. It
# can be removed when fully do things the flasky way.

from __future__ import annotations

import logging
from typing import List, Optional, TYPE_CHECKING

from werkzeug.local import LocalStack

from cmk.gui.utils.user_errors import UserErrors

if TYPE_CHECKING:
    # Cyclical import
    from cmk.gui import htmllib, http, userdb
    from cmk.gui.config import Config
    from cmk.gui.display_options import DisplayOptions
    from cmk.gui.i18n import Translation
    from cmk.gui.logged_in import LoggedInUser
    from cmk.gui.plugins.openapi.restful_objects import Endpoint
    from cmk.gui.utils.output_funnel import OutputFunnel
    from cmk.gui.utils.theme import Theme
    from cmk.gui.utils.timeout_manager import TimeoutManager
    from cmk.gui.utils.transaction_manager import TransactionManager

_sentinel = object()


class _AppCtxGlobals:
    def get(self, name, default=None):
        return self.__dict__.get(name, default)

    def pop(self, name, default=_sentinel):
        if default is _sentinel:
            return self.__dict__.pop(name)
        return self.__dict__.pop(name, default)

    def setdefault(self, name, default=None):
        return self.__dict__.setdefault(name, default)

    def __contains__(self, item):
        return item in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)


class AppContext:
    """Application state handling during a request

    The application context keeps track of the application-level data during a request, CLI
    command, or other activity. Rather than passing the application around to each function, the
    current_app and g proxies are accessed instead.

    This is similar to the The Request Context, which keeps track of request-level data during a
    request. A corresponding application context is pushed when a request context is pushed.

    The application context is a good place to store common data during a request or CLI command.

    See:

        https://flask.palletsprojects.com/en/1.1.x/appcontext/
        https://flask.palletsprojects.com/en/1.1.x/reqcontext/
    """

    def __init__(self, app, *, stack: LocalStack):
        self.app = app
        self.g = _AppCtxGlobals()
        self._stack = stack

    def __enter__(self):
        self._stack.push(self)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._stack.pop()


class RequestContext:
    """
    The request context keeps track of the request-level data during a request. Rather than passing
    the request object to each function that runs during a request, the request and session proxies
    are accessed instead.

    This is similar to the The Application Context, which keeps track of the application-level data
    independent of a request. A corresponding application context is pushed when a request context is
    pushed.

    When a Flask application begins handling a request, it pushes a request context, which also
    pushes an The Application Context. When the request ends it pops the request context then the
    application context.

    The context is unique to each thread (or other worker type). request cannot be passed to another
    thread, the other thread will have a different context stack and will not know about the request
    the parent thread was pointing to.

    See:

        https://flask.palletsprojects.com/en/1.1.x/appcontext/
        https://flask.palletsprojects.com/en/1.1.x/reqcontext/
    """

    def __init__(
        self,
        req: http.Request,
        resp: http.Response,
        funnel: OutputFunnel,
        config_obj: Config,
        user: LoggedInUser,  # pylint: disable=redefined-outer-name
        html_obj: Optional[htmllib.html] = None,
        timeout_manager: Optional[TimeoutManager] = None,  # pylint: disable=redefined-outer-name
        theme: Optional[Theme] = None,  # pylint: disable=redefined-outer-name
        display_options: Optional[DisplayOptions] = None,  # pylint: disable=redefined-outer-name
        prefix_logs_with_url: bool = True,
        endpoint: Optional[Endpoint] = None,  # pylint: disable=redefined-outer-name
        *,
        stack: LocalStack,
        url_filter: logging.Filter,
    ):
        self.html = html_obj
        self.auth_type: Optional[str] = None
        self.timeout_manager = timeout_manager
        self.theme = theme
        self.display_options = display_options
        self.session: Optional[userdb.Session] = None
        self.flashes: Optional[List[str]] = None
        self.translation: Optional[Translation] = None
        self._prefix_logs_with_url = prefix_logs_with_url

        self.endpoint = endpoint
        self.request = req
        self.response = resp
        self.output_funnel = funnel
        self.config = config_obj
        self._user = user
        self.user_errors = UserErrors()

        self._prepend_url_filter = url_filter
        self._web_log_handler: Optional[logging.Handler] = None

        self._stack = stack

    @property
    def user(self) -> LoggedInUser:
        return self._user

    @user.setter
    def user(self, user_obj: LoggedInUser) -> None:
        self._user = user_obj

    @property
    def transactions(self) -> TransactionManager:
        return self._user.transactions

    def __enter__(self):
        self._stack.push(self)
        # TODO: Move this plus the corresponding cleanup code to hooks.
        if self._prefix_logs_with_url:
            self._web_log_handler = logging.getLogger().handlers[0]
            self._web_log_handler.addFilter(self._prepend_url_filter)

        _call_hook("request-context-enter")

        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self._web_log_handler is not None:
            self._web_log_handler.removeFilter(self._prepend_url_filter)

        if self.timeout_manager is not None:
            self.timeout_manager.disable_timeout()

        _call_hook("request-context-exit")

        self._stack.pop()


def _call_hook(name: str) -> None:
    from cmk.gui import hooks

    hooks.call(name)
