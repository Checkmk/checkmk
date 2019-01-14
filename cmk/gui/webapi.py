#!/usr/bin/python
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

import traceback
import json
import pprint
import xml.dom.minidom  # type: ignore

import dicttoxml  # type: ignore

import cmk

import cmk.gui.pages
from cmk.gui.log import logger
import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.watolib.read_only
import cmk.gui.i18n
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import (
    MKUserError,
    MKAuthException,
    MKException,
)

import cmk.gui.plugins.webapi

if not cmk.is_raw_edition():
    import cmk.gui.cee.plugins.webapi

# TODO: Kept for compatibility reasons with legacy plugins
from cmk.gui.plugins.webapi.utils import (  # pylint: disable=unused-import
    add_configuration_hash, api_call_collection_registry, check_hostname, validate_config_hash,
    validate_host_attributes, validate_request_keys,
)

loaded_with_language = False


def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    utils.load_web_plugins("webapi", globals())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()

    config.declare_permission("wato.api_allowed", _("Access to Web-API"),
                                                  _("This permissions specifies if the role "\
                                                    "is able to use Web-API functions. It is only available "\
                                                    "for automation users."),
                              config.builtin_role_ids)


_FORMATTERS = {
    "json": (
        json.dumps,
        lambda response: json.dumps(response, sort_keys=True, indent=4, separators=(',', ': '))),
    "python": (repr, pprint.pformat),
    "xml": (
        dicttoxml.dicttoxml,
        lambda response: xml.dom.minidom.parseString(dicttoxml.dicttoxml(response)).toprettyxml()),
}


@cmk.gui.pages.register("webapi")
def page_api():
    try:
        pretty_print = False
        if not html.request.has_var("output_format"):
            html.set_output_format("json")
        if html.output_format not in _FORMATTERS:
            html.set_output_format("python")
            raise MKUserError(
                None, "Only %s are supported as output formats" % " and ".join(
                    '"%s"' % f for f in _FORMATTERS))

        # TODO: Add some kind of helper for boolean-valued variables?
        pretty_print_var = html.request.var("pretty_print", "no").lower()
        if pretty_print_var not in ("yes", "no"):
            raise MKUserError(None, 'pretty_print must be "yes" or "no"')
        pretty_print = pretty_print_var == "yes"

        if not config.user.get_attribute("automation_secret"):
            raise MKAuthException("The WATO API is only available for automation users")

        if not config.wato_enabled:
            raise MKUserError(None, _("WATO is disabled on this site."))

        config.user.need_permission("wato.use")
        config.user.need_permission("wato.api_allowed")

        action = html.request.var('action')
        api_call = api_call_collection_registry.get(action)
        if not api_call:
            raise MKUserError(None, "Unknown API action %s" % html.attrencode(action))

        for permission in api_call.get("required_permissions", []):
            config.user.need_permission(permission)

        # Initialize host and site attributes
        watolib.init_wato_datastructures()

        # Prepare request_object
        # Most of the time the request is given as json
        # However, the plugin may have an own mechanism to interpret the request
        request_object = {}
        if api_call.get("dont_eval_request"):
            if html.request.var("request"):
                request_object = html.request.var("request")
        else:
            request_object = html.get_request(exclude_vars=["action", "pretty_print"])

        # Check if the data was sent with the correct data format
        # Some API calls only allow python code
        # TODO: convert the api_action dict into an object which handles the validation
        required_input_format = api_call.get("required_input_format")
        if required_input_format:
            if required_input_format != request_object["request_format"]:
                raise MKUserError(
                    None,
                    "This API call requires a %s-encoded request parameter" % required_input_format)

        required_output_format = api_call.get("required_output_format")
        if required_output_format:
            if required_output_format != html.output_format:
                raise MKUserError(
                    None, "This API call requires the parameter output_format=%s" %
                    required_output_format)

        # The request_format parameter is not forwarded into the API action
        if "request_format" in request_object:
            del request_object["request_format"]

        def execute_action():
            if cmk.gui.watolib.read_only.is_enabled(
            ) and not cmk.gui.watolib.read_only.may_override():
                raise MKUserError(None, cmk.gui.watolib.read_only.message())
            return {
                "result_code": 0,
                "result": api_call["handler"](request_object),
            }

        if api_call.get("locking", True):
            with watolib.exclusive_lock():
                response = execute_action()
        else:
            response = execute_action()

    except MKAuthException as e:
        response = {
            "result_code": 1,
            "result": _("Authorization Error. Insufficent permissions for '%s'") % e
        }
    except MKException as e:
        response = {"result_code": 1, "result": _("Check_MK exception: %s") % e}
    except Exception as e:
        if config.debug:
            raise
        logger.exception()
        response = {
            "result_code": 1,
            "result": _("Unhandled exception: %s") % traceback.format_exc(),
        }

    html.write(_FORMATTERS[html.output_format][1 if pretty_print else 0](response))
