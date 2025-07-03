#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
import http.client as http_client
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

import cmk.ccc.plugin_registry
from cmk.ccc.exceptions import MKException

from cmk.gui.config import Config
from cmk.gui.crash_handler import handle_exception_as_gui_crash_report
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.log import logger
from cmk.gui.utils.json import CustomObjectJSONEncoder

PageHandlerFunc = Callable[[Config], None]
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
    def handle_page(self, config: Config) -> None:
        self.page(config)

    @abc.abstractmethod
    def page(self, config: Config) -> PageResult:
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

    def _handle_exc(self, config: Config, method: Callable[[Config], PageResult]) -> None:
        try:
            method(config)
        except MKException as e:
            response.status_code = http_client.BAD_REQUEST
            html.write_text_permissive(str(e))
        except Exception as e:
            response.status_code = http_client.INTERNAL_SERVER_ERROR
            if config.debug:
                raise
            logger.exception("error calling AJAX page handler")
            handle_exception_as_gui_crash_report(
                plain_error=True,
                show_crash_link=getattr(g, "may_see_crash_reports", False),
            )
            html.write_text_permissive(str(e))

    @override
    def handle_page(self, config: Config) -> None:
        """The page handler, called by the page registry"""
        response.set_content_type("application/json")
        try:
            action_response = self.page(config)
            resp = {"result_code": 0, "result": action_response, "severity": "success"}
        except MKMissingDataError as e:
            resp = {"result_code": 1, "result": str(e), "severity": "success"}
        except MKException as e:
            resp = {"result_code": 1, "result": str(e), "severity": "error"}

        except Exception as e:
            if config.debug:
                raise
            logger.exception("error calling AJAX page handler")
            handle_exception_as_gui_crash_report(
                plain_error=True,
                show_crash_link=getattr(g, "may_see_crash_reports", False),
            )
            resp = {"result_code": 1, "result": str(e), "severity": "error"}

        response.set_data(json.dumps(resp, cls=CustomObjectJSONEncoder))


@dataclass(frozen=True)
class PageEndpoint:
    ident: str
    handler: PageHandlerFunc | type[Page]


class PageRegistry(cmk.ccc.plugin_registry.Registry[PageEndpoint]):
    @override
    def plugin_name(self, instance: PageEndpoint) -> str:
        return instance.ident


page_registry = PageRegistry()


def get_page_handler(
    name: str, dflt: PageHandlerFunc | None = None
) -> PageHandlerFunc | type[Page] | None:
    """Returns either the page handler registered for the given name or None

    In case dflt is given it returns dflt instead of None when there is no
    page handler for the requested name."""
    if endpoint := page_registry.get(name):
        return endpoint.handler
    return dflt
