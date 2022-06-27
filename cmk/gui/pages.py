#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import http.client as http_client
import inspect
import json
from typing import Any, Callable, Dict, Optional, Type

import cmk.utils.plugin_registry
from cmk.utils.exceptions import MKException

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

    def webapi_request(self) -> Dict[str, Any]:
        return request.get_request()

    @abc.abstractmethod
    def page(self) -> PageResult:
        """Override this to implement the page functionality"""
        raise NotImplementedError()

    def _handle_exc(self, method) -> None:
        try:
            # FIXME: These methods write to the response themselves. This needs to be refactored.
            method()
        except MKException as e:
            response.status_code = http_client.BAD_REQUEST
            html.write_text(str(e))
        except Exception as e:
            response.status_code = http_client.INTERNAL_SERVER_ERROR
            if active_config.debug:
                raise
            logger.exception("error calling AJAX page handler")
            handle_exception_as_gui_crash_report(
                plain_error=True,
                show_crash_link=getattr(g, "may_see_crash_reports", False),
            )
            html.write_text(str(e))

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


class PageRegistry(cmk.utils.plugin_registry.Registry[Type[Page]]):
    def plugin_name(self, instance: Type[Page]) -> str:
        return instance.ident()

    def register_page(self, path: str) -> Callable[[Type[Page]], Type[Page]]:
        def wrap(plugin_class: Type[Page]) -> Type[Page]:
            if not inspect.isclass(plugin_class):
                raise NotImplementedError()

            # mypy is not happy with this. Find a cleaner way
            plugin_class._ident = path
            plugin_class.ident = classmethod(lambda cls: cls._ident)

            self.register(plugin_class)
            return plugin_class

        return wrap


page_registry = PageRegistry()


# TODO: Refactor all call sites to sub classes of Page() and change the
# registration to page_registry.register("path")
def register(path: str) -> Callable[[PageHandlerFunc], PageHandlerFunc]:
    """Register a function to be called when the given URL is called.

    In case you need to register some callable like staticmethods or
    classmethods, you will have to use register_page_handler() directly
    because this decorator can not deal with them.

    It is essentially a decorator that calls register_page_handler().
    """

    def wrap(wrapped_callable: PageHandlerFunc) -> PageHandlerFunc:
        cls_name = "PageClass%s" % path.title().replace(":", "")
        LegacyPageClass = type(
            cls_name,
            (Page,),
            {
                "_wrapped_callable": (wrapped_callable,),
                "page": lambda self: self._wrapped_callable[0](),
            },
        )

        page_registry.register_page(path)(LegacyPageClass)
        return lambda: LegacyPageClass().handle_page()

    return wrap


# TODO: replace all call sites by directly calling page_registry.register_page("path")
def register_page_handler(path: str, page_func: PageHandlerFunc) -> PageHandlerFunc:
    """Register a function to be called when the given URL is called."""
    wrap = register(path)
    return wrap(page_func)


def get_page_handler(
    name: str, dflt: Optional[PageHandlerFunc] = None
) -> Optional[PageHandlerFunc]:
    """Returns either the page handler registered for the given name or None

    In case dflt is given it returns dflt instead of None when there is no
    page handler for the requested name."""

    def page_handler(hc: Type[Page]) -> PageHandlerFunc:
        return lambda: hc().handle_page()

    return dflt if (handle_class := page_registry.get(name)) is None else page_handler(handle_class)
