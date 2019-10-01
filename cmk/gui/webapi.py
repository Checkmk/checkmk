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

import cmk.utils.store as store

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
from cmk.gui.plugins.wato.utils import PermissionSectionWATO
from cmk.gui.permissions import (
    permission_registry,
    Permission,
)

import cmk.gui.plugins.webapi

if not cmk.is_raw_edition():
    import cmk.gui.cee.plugins.webapi

# TODO: Kept for compatibility reasons with legacy plugins
from cmk.gui.plugins.webapi.utils import (  # pylint: disable=unused-import
    add_configuration_hash, api_call_collection_registry, check_hostname, validate_config_hash,
    validate_host_attributes,
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


@permission_registry.register
class PermissionWATOAllowedAPI(Permission):
    @property
    def section(self):
        return PermissionSectionWATO

    @property
    def permission_name(self):
        return "api_allowed"

    @property
    def title(self):
        return _("Access to Web-API")

    @property
    def description(self):
        return _("This permissions specifies if the role "
                 "is able to use Web-API functions. It is only available "
                 "for automation users.")

    @property
    def defaults(self):
        return config.builtin_role_ids


_FORMATTERS = {
    "json":
        (json.dumps,
         lambda response: json.dumps(response, sort_keys=True, indent=4, separators=(',', ': '))),
    "python": (repr, pprint.pformat),
    "xml":
        (dicttoxml.dicttoxml,
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
                None, "Only %s are supported as output formats" %
                " and ".join('"%s"' % f for f in _FORMATTERS))

        # TODO: Add some kind of helper for boolean-valued variables?
        pretty_print_var = html.request.var("pretty_print", "no").lower()
        if pretty_print_var not in ("yes", "no"):
            raise MKUserError(None, 'pretty_print must be "yes" or "no"')
        pretty_print = pretty_print_var == "yes"

        api_call = _get_api_call()
        _check_permissions(api_call)
        watolib.init_wato_datastructures()  # Initialize host and site attributes
        request_object = _get_request(api_call)
        _check_formats(api_call, request_object)
        _check_request_keys(api_call, request_object)
        response = _execute_action(api_call, request_object)

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
        logger.exception("error handling web API call")
        response = {
            "result_code": 1,
            "result": _("Unhandled exception: %s") % traceback.format_exc(),
        }

    html.write(_FORMATTERS[html.output_format][1 if pretty_print else 0](response))


# TODO: If the registered API calls were instance of a real class, all the code
# below would be in methods of that class.


def _get_api_call():
    action = html.request.var('action')
    for cls in api_call_collection_registry.values():
        api_call = cls().get_api_calls().get(action)
        if api_call:
            return api_call
    raise MKUserError(None, "Unknown API action %s" % html.attrencode(action))


def _check_permissions(api_call):
    if not config.user.get_attribute("automation_secret"):
        raise MKAuthException("The WATO API is only available for automation users")

    if not config.wato_enabled:
        raise MKUserError(None, _("WATO is disabled on this site."))

    for permission in ["wato.use", "wato.api_allowed"] + \
                      api_call.get("required_permissions", []):
        config.user.need_permission(permission)


def _get_request(api_call):
    if api_call.get("dont_eval_request"):
        return html.request.var("request", {})
    return html.get_request(exclude_vars=["action", "pretty_print"])


def _check_formats(api_call, request_object):
    required_input_format = api_call.get("required_input_format")
    if required_input_format and required_input_format != request_object["request_format"]:
        raise MKUserError(
            None, "This API call requires a %s-encoded request parameter" % required_input_format)

    required_output_format = api_call.get("required_output_format")
    if required_output_format and required_output_format != html.output_format:
        raise MKUserError(
            None, "This API call requires the parameter output_format=%s" % required_output_format)

    # The request_format parameter is not forwarded into the API action
    if "request_format" in request_object:
        del request_object["request_format"]


def _check_request_keys(api_call, request_object):
    required_keys = set(api_call.get("required_keys", []))
    optional_keys = set(api_call.get("optional_keys", []))
    actual_keys = set(request_object.keys())

    missing_keys = required_keys - actual_keys
    if missing_keys:
        raise MKUserError(None, _("Missing required key(s): %s") % ", ".join(missing_keys))

    invalid_keys = actual_keys - (required_keys | optional_keys)
    if invalid_keys:
        raise MKUserError(None, _("Invalid key(s): %s") % ", ".join(invalid_keys))


def _execute_action(api_call, request_object):
    if api_call.get("locking", True):
        with store.lock_checkmk_configuration():
            return _execute_action_no_lock(api_call, request_object)
    return _execute_action_no_lock(api_call, request_object)


def _execute_action_no_lock(api_call, request_object):
    if cmk.gui.watolib.read_only.is_enabled() and \
       not cmk.gui.watolib.read_only.may_override():
        raise MKUserError(None, cmk.gui.watolib.read_only.message())
    return {
        "result_code": 0,
        "result": api_call["handler"](request_object),
    }
