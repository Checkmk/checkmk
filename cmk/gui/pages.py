#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import abc
import json
from cmk.gui.globals import html
import cmk.gui.config as config
from cmk.gui.exceptions import MKException
from cmk.gui.log import logger

_pages = {}


def register(path):
    """Register a function to be called when the given URL is called.

    In case you need to register some callable like staticmethods or
    classmethods, you will have to use register_page_handler() directly
    because this decorator can not deal with them.

    It is essentially a decorator that calls register_page_handler().
    """

    def wrap(page_func):
        if isinstance(page_func, (staticmethod, classmethod)):
            raise NotImplementedError()

        register_page_handler(path, page_func)
        return page_func

    return wrap


def register_page_handler(path, page_func):
    """Register a function to be called when the given URL is called."""
    _pages[path] = page_func


def get_page_handler(name, dflt=None):
    """Returns either the page handler registered for the given name or None

    In case dflt is given it returns dflt instead of None when there is no
    page handler for the requested name."""
    return _pages.get(name, dflt)


# TODO: Clean up implicit _from_vars() procotocol
class AjaxPage(object):
    """Generic page handler that wraps page() calls into AJAX respones"""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def page(self):
        """Override this to implement the page functionality"""
        raise NotImplementedError()

    def __init__(self):
        super(AjaxPage, self).__init__()
        self._from_vars()

    def _from_vars(self):
        """Override this method to set mode specific attributes based on the
        given HTTP variables."""
        pass

    def webapi_request(self):
        return html.get_request()

    def handle_page(self):
        """The page handler, called by the page registry"""
        html.set_output_format("json")
        try:
            action_response = self.page()
            response = {"result_code": 0, "result": action_response}
        except MKException as e:
            response = {"result_code": 1, "result": "%s" % e}

        except Exception as e:
            if config.debug:
                raise
            logger.exception()
            response = {"result_code": 1, "result": "%s" % e}

        html.write(json.dumps(response))
