#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import pprint
import traceback
import xml.dom.minidom  # type: ignore[import]
from typing import Any, Callable, Dict, Tuple

import dicttoxml  # type: ignore[import]

import cmk.utils.store as store

import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.utils as utils
import cmk.gui.utils.escaping as escaping
import cmk.gui.watolib
import cmk.gui.watolib.read_only
from cmk.gui.config import builtin_role_ids
from cmk.gui.exceptions import MKAuthException, MKException, MKUserError
from cmk.gui.globals import config, request, response, user
from cmk.gui.i18n import _, _l
from cmk.gui.log import logger
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.plugins.wato.utils import PermissionSectionWATO

# TODO: Kept for compatibility reasons with legacy plugins
from cmk.gui.plugins.webapi.utils import (  # noqa: F401 # pylint: disable=unused-import
    add_configuration_hash,
    api_call_collection_registry,
    APICallDefinitionDict,
    check_hostname,
    validate_config_hash,
)
from cmk.gui.watolib.activate_changes import update_config_generation


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    utils.load_web_plugins("webapi", globals())


permission_registry.register(
    Permission(
        section=PermissionSectionWATO,
        name="api_allowed",
        title=_l("Access to Web-API"),
        description=_l(
            "This permissions specifies if the role "
            "is able to use Web-API functions. It is only available "
            "for automation users."
        ),
        defaults=builtin_role_ids,
    )
)

Formatter = Callable[[Dict[str, Any]], str]

_FORMATTERS: Dict[str, Tuple[Formatter, Formatter]] = {
    "json": (
        json.dumps,
        lambda resp: json.dumps(resp, sort_keys=True, indent=4, separators=(",", ": ")),
    ),
    "python": (repr, pprint.pformat),
    "xml": (
        dicttoxml.dicttoxml,
        lambda resp: xml.dom.minidom.parseString(dicttoxml.dicttoxml(resp)).toprettyxml(),
    ),
}


@cmk.gui.pages.register("webapi")
def page_api() -> None:
    try:
        if not request.has_var("output_format"):
            response.set_content_type("application/json")
            output_format = "json"
        else:
            output_format = request.get_ascii_input_mandatory("output_format", "json").lower()

        if output_format not in _FORMATTERS:
            response.set_content_type("text/plain")
            raise MKUserError(
                None,
                "Only %s are supported as output formats"
                % " and ".join('"%s"' % f for f in _FORMATTERS),
            )

        # TODO: Add some kind of helper for boolean-valued variables?
        pretty_print = False
        pretty_print_var = request.get_str_input_mandatory("pretty_print", "no").lower()
        if pretty_print_var not in ("yes", "no"):
            raise MKUserError(None, 'pretty_print must be "yes" or "no"')
        pretty_print = pretty_print_var == "yes"

        api_call = _get_api_call()
        _check_permissions(api_call)
        request_object = _get_request(api_call)
        _check_formats(output_format, api_call, request_object)
        _check_request_keys(api_call, request_object)
        resp = _execute_action(api_call, request_object)

    except MKAuthException as e:
        resp = {
            "result_code": 1,
            "result": _("Authorization Error. Insufficent permissions for '%s'") % e,
        }
    except MKException as e:
        resp = {
            "result_code": 1,
            "result": _("Checkmk exception: %s\n%s") % (e, "".join(traceback.format_exc())),
        }
    except Exception:
        if config.debug:
            raise
        logger.exception("error handling web API call")
        resp = {
            "result_code": 1,
            "result": _("Unhandled exception: %s") % traceback.format_exc(),
        }

    response.set_data(_FORMATTERS[output_format][1 if pretty_print else 0](resp))


# TODO: If the registered API calls were instance of a real class, all the code
# below would be in methods of that class.


def _get_api_call() -> APICallDefinitionDict:
    action = request.get_str_input_mandatory("action")
    for cls in api_call_collection_registry.values():
        api_call = cls().get_api_calls().get(action)
        if api_call:
            return api_call
    raise MKUserError(None, "Unknown API action %s" % escaping.escape_attribute(action))


def _check_permissions(api_call: APICallDefinitionDict) -> None:
    if not user.get_attribute("automation_secret"):
        raise MKAuthException("The API is only available for automation users")

    if not config.wato_enabled:
        raise MKUserError(None, _("Setup is disabled on this site."))

    for permission in ["wato.use", "wato.api_allowed"] + api_call.get("required_permissions", []):
        user.need_permission(permission)


def _get_request(api_call: APICallDefinitionDict) -> dict[str, Any]:
    return request.get_request(exclude_vars=["action", "pretty_print"])


def _check_formats(
    output_format: str, api_call: APICallDefinitionDict, request_object: dict[str, Any]
):
    required_input_format = api_call.get("required_input_format")
    if required_input_format and required_input_format != request_object["request_format"]:
        raise MKUserError(
            None, "This API call requires a %s-encoded request parameter" % required_input_format
        )

    required_output_format = api_call.get("required_output_format")
    if required_output_format and required_output_format != output_format:
        raise MKUserError(
            None, "This API call requires the parameter output_format=%s" % required_output_format
        )

    # The request_format parameter is not forwarded into the API action
    request_object.pop("request_format", None)


def _check_request_keys(api_call: APICallDefinitionDict, request_object: dict[str, Any]) -> None:
    required_keys = set(api_call.get("required_keys", []))
    optional_keys = set(api_call.get("optional_keys", []))
    actual_keys = set(request_object.keys())

    missing_keys = required_keys - actual_keys
    if missing_keys:
        raise MKUserError(None, _("Missing required key(s): %s") % ", ".join(missing_keys))

    invalid_keys = actual_keys - (required_keys | optional_keys)
    if invalid_keys:
        raise MKUserError(None, _("Invalid key(s): %s") % ", ".join(invalid_keys))


def _execute_action(
    api_call: APICallDefinitionDict, request_object: dict[str, Any]
) -> dict[str, Any]:
    if api_call.get("locking", True):
        with store.lock_checkmk_configuration():
            return _execute_action_no_lock(api_call, request_object)
    return _execute_action_no_lock(api_call, request_object)


def _execute_action_no_lock(
    api_call: APICallDefinitionDict, request_object: dict[str, Any]
) -> dict[str, Any]:
    if cmk.gui.watolib.read_only.is_enabled() and not cmk.gui.watolib.read_only.may_override():
        raise MKUserError(None, cmk.gui.watolib.read_only.message())

    # We assume something will be modified and increase the config generation
    update_config_generation()

    return {
        "result_code": 0,
        "result": api_call["handler"](request_object),
    }
