#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
import functools
import http.client as http_client
import json
from collections.abc import Callable
from typing import Any

import cmk.ccc.plugin_registry
from cmk.ccc.exceptions import MKException

from cmk.gui.config import active_config
from cmk.gui.crash_handler import handle_exception_as_gui_crash_report
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.log import logger

PageHandlerFunc = Callable[[], None]
PageResult = object


# At the moment pages are simply callables that somehow render content for the HTTP response
# and send it to the client.
#
# At least for HTML pages we should standardize the pages a bit more since there are things all pages do
# - Create a title, render the header
# - Have a breadcrumb
# - Optional: Handle actions
# - Render the page
#
# TODO: Check out the WatoMode class and find out how to do this. Looks like handle_page() could
# implement parts of the cmk.gui.wato.page_handler.page_handler() logic.
class Page(abc.ABC):
    # TODO: In theory a page class could be registered below multiple URLs. For this case it would
    # be better to move the ident out of the class, to the registry. At the moment the URL is stored
    # in self._ident by PageRegistry.register_page().
    # In practice this is no problem at the moment, because each page is accessible only through a
    # single endpoint.

    @classmethod
    def ident(cls) -> str:
        raise NotImplementedError()

    def handle_page(self) -> None:
        self.page()

    @abc.abstractmethod
    def page(self) -> PageResult:
        """Override this to implement the page functionality"""
        raise NotImplementedError()


# TODO: Clean up implicit _from_vars() procotocol
class AjaxPage(Page, abc.ABC):
    """Generic page handler that wraps page() calls into AJAX respones"""

    def __init__(self) -> None:
        super().__init__()
        self._from_vars()

    def _from_vars(self) -> None:
        """Override this method to set mode specific attributes based on the
        given HTTP variables."""

    def webapi_request(self) -> dict[str, Any]:
        return request.get_request()

    @abc.abstractmethod
    def page(self) -> PageResult:
        """Override this to implement the page functionality"""
        raise NotImplementedError()

    def _handle_exc(self, method: Callable[[], PageResult]) -> None:
        try:
            method()
        except MKException as e:
            response.status_code = http_client.BAD_REQUEST
            html.write_text_permissive(str(e))
        except Exception as e:
            response.status_code = http_client.INTERNAL_SERVER_ERROR
            if active_config.debug:
                raise
            logger.exception("error calling AJAX page handler")
            handle_exception_as_gui_crash_report(
                plain_error=True,
                show_crash_link=getattr(g, "may_see_crash_reports", False),
            )
            html.write_text_permissive(str(e))

    def handle_page(self) -> None:
        """The page handler, called by the page registry"""
        response.set_content_type("application/json")
        try:
            action_response = self.page()
            resp = {"result_code": 0, "result": action_response, "severity": "success"}
        except MKMissingDataError as e:
            resp = {"result_code": 1, "result": str(e), "severity": "success"}
        except MKException as e:
            resp = {"result_code": 1, "result": str(e), "severity": "error"}

        except Exception as e:
            if active_config.debug:
                raise
            logger.exception("error calling AJAX page handler")
            handle_exception_as_gui_crash_report(
                plain_error=True,
                show_crash_link=getattr(g, "may_see_crash_reports", False),
            )
            resp = {"result_code": 1, "result": str(e), "severity": "error"}

        response.set_data(json.dumps(resp))


class PageRegistry(cmk.ccc.plugin_registry.Registry[type[Page]]):
    def plugin_name(self, instance: type[Page]) -> str:
        return instance.ident()

    def register_page(self, path: str) -> Callable[[type[Page]], type[Page]]:
        def wrap(plugin_class: type[Page]) -> type[Page]:
            if not isinstance(plugin_class, type):
                raise NotImplementedError()

            # mypy is not happy with this. Find a cleaner way
            plugin_class._ident = path  # type: ignore[attr-defined]
            plugin_class.ident = classmethod(lambda cls: cls._ident)  # type: ignore[assignment]

            self.register(plugin_class)
            return plugin_class

        return wrap

    def register_page_handler(self, path: str, page_handler: PageHandlerFunc) -> type[Page]:
        cls_name = "PageClass%s" % path.title().replace(":", "")
        cls = type(
            cls_name,
            (Page,),
            {
                "_wrapped_callable": (page_handler,),
                "page": lambda self: self._wrapped_callable[0](),
            },
        )
        self.register_page(path)(cls)
        return cls


page_registry = PageRegistry()


def get_page_handler(name: str, dflt: PageHandlerFunc | None = None) -> PageHandlerFunc | None:
    """Returns either the page handler registered for the given name or None

    In case dflt is given it returns dflt instead of None when there is no
    page handler for the requested name."""

    def page_handler(hc: type[Page]) -> PageHandlerFunc:
        # We pretend to wrap `hc.page` instead of `hc.handle_page`, because `hc.handle_page` is
        # usually only defined on the superclass, which doesn't really help in debugging. The
        # instance is not shown, and it is not 100% correct, but it's better than nothing at all.
        @functools.wraps(hc.page)
        def wrapper():
            return hc().handle_page()

        return wrapper

    if handle_class := page_registry.get(name):
        return page_handler(handle_class)

    return dflt
