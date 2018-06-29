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

from lib import *
import config
import watolib
import userdb

from valuespec import *

if cmk.is_managed_edition():
    import managed
else:
    managed = None

import json

api_actions = {}
loaded_with_language = False


#.
#   .--API Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
# TODO: encapsulate in module/class

def validate_request_keys(request, required_keys = None, optional_keys = None):
    if required_keys:
        missing = set(required_keys) - set(request.keys())
        if missing:
            raise MKUserError(None, _("Missing required key(s): %s") % ", ".join(missing))


    all_keys = (required_keys or []) + (optional_keys or [])
    for key in request.keys():
        if key not in all_keys:
            raise MKUserError(None, _("Invalid key: %s") % key)


def check_hostname(hostname, should_exist = True):
    # Validate hostname with valuespec
    Hostname().validate_value(hostname, "hostname")

    if should_exist:
        host = watolib.Host.host(hostname)
        if not host:
            raise MKUserError(None, _("No such host"))
    else:
        if watolib.Host.host_exists(hostname):
            raise MKUserError(None, _("Host %s already exists in the folder %s") % (hostname, watolib.Host.host(hostname).folder().path()))


# Check if the given attribute name exists, no type check
def validate_general_host_attributes(host_attributes):
    # inventory_failed and site are no "real" host_attributes (TODO: Clean this up!)
    all_host_attribute_names = map(lambda (x, y): x.name(), watolib.all_host_attributes()) + ["inventory_failed", "site"]
    for name, value in host_attributes.items():
        if name not in all_host_attribute_names:
            raise MKUserError(None, _("Unknown attribute: %s") % html.attrencode(name))

        # For real host attributes validate the values
        try:
            attr = watolib.host_attribute(name)
        except KeyError:
            attr = None

        if attr != None:
            if attr.needs_validation("host"):
                attr.validate_input(value, "")

        # The site attribute gets an extra check
        if name == "site" and value not in config.allsites().keys():
            raise MKUserError(None, _("Unknown site %s") % html.attrencode(value))


# Check if the tag group exists and the tag value is valid
def validate_host_tags(host_tags):
    for key, value in host_tags.items():
        for group_entry in config.host_tag_groups():
            if group_entry[0] == key:
                for value_entry in group_entry[2]:
                    if value_entry[0] == value:
                        break
                else:
                    raise MKUserError(None, _("Unknown host tag %s") % html.attrencode(value))
                break
        else:
            raise MKUserError(None, _("Unknown host tag group %s") % html.attrencode(key))


def validate_host_attributes(attributes):
    validate_general_host_attributes(dict((key, value) for key, value in attributes.items() if not key.startswith("tag_")))
    validate_host_tags(dict((key[4:], value) for key, value in attributes.items() if key.startswith("tag_")))


def compute_config_hash(entity):
    import json, md5
    try:
        entity_encoded = json.dumps(entity, sort_keys=True)
        entity_hash    = md5.md5(entity_encoded).hexdigest()
    except Exception, e:
        logger.error("Error %s" % e)
        entity_hash = "0"

    return entity_hash


def validate_config_hash(hash_value, entity):
    entity_hash = compute_config_hash(entity)
    if hash_value != entity_hash:
        raise MKUserError(None, _("The configuration has changed in the meantime. "\
                                  "You need to load the configuration and start another update. "
                                  "If the existing configuration should not be checked, you can "
                                  "remove the configuration_hash value from the request object."))


def add_configuration_hash(response, configuration_object):
    response["configuration_hash"] = compute_config_hash(configuration_object)


class APICallCollection(object):
    @classmethod
    def all_classes(cls):
        classes = {}
        for subclass in cls.__subclasses__(): # pylint: disable=no-member
            classes[subclass.__name__] = subclass

        return classes.values()


    def get_api_calls(self):
        raise NotImplementedError("This API collection does not register any API call")



def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == current_language and not force:
        return

    load_web_plugins("webapi", globals())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language

    config.declare_permission("wato.api_allowed", _("Access to Web-API"),
                                                  _("This permissions specifies if the role "\
                                                    "is able to use Web-API functions. It is only available "\
                                                    "for automation users."),
                              config.builtin_role_ids)


def page_api():
    try:
        # The API uses JSON format by default and python as optional alternative
        output_format = html.var("output_format", "json")
        if output_format not in [ "json", "python" ]:
            raise MKUserError(None, "Only \"json\" and \"python\" are supported as output formats")
        else:
            html.set_output_format(output_format)

        if not config.user.get_attribute("automation_secret"):
            raise MKAuthException("The WATO API is only available for automation users")

        if not config.wato_enabled:
            raise MKUserError(None, _("WATO is disabled on this site."))

        config.user.need_permission("wato.use")
        config.user.need_permission("wato.api_allowed")


        action = html.var('action')
        if action not in api_actions:
            raise MKUserError(None, "Unknown API action %s" % html.attrencode(action))


        for permission in api_actions[action].get("required_permissions", []):
            config.user.need_permission(permission)

        # Initialize host and site attributes
        watolib.init_watolib_datastructures()

        # Prepare request_object
        # Most of the time the request is given as json
        # However, the plugin may have an own mechanism to interpret the request
        request_object = {}
        if api_actions[action].get("dont_eval_request"):
            if html.var("request"):
                request_object = html.var("request")
        else:
            request_object = html.get_request(exclude_vars=["action"])


        # Check if the data was sent with the correct data format
        # Some API calls only allow python code
        # TODO: convert the api_action dict into an object which handles the validation
        required_input_format = api_actions[action].get("required_input_format")
        if required_input_format:
            if required_input_format != request_object["request_format"]:
                raise MKUserError(None, "This API call requires a %s-encoded request parameter" % required_input_format)

        required_output_format = api_actions[action].get("required_output_format")
        if required_output_format:
            if required_output_format != html.output_format:
                raise MKUserError(None, "This API call requires the parameter output_format=%s" % required_output_format)


        # The request_format parameter is not forwarded into the API action
        if "request_format" in request_object:
            del request_object["request_format"]

        if api_actions[action].get("locking", True):
            watolib.lock_exclusive() # unlock is done automatically

        if watolib.is_read_only_mode_enabled() and not watolib.may_override_read_only_mode():
            raise MKUserError(None, watolib.read_only_message())

        action_response = api_actions[action]["handler"](request_object)
        response = { "result_code": 0, "result": action_response }

    except MKAuthException, e:
        response = { "result_code": 1, "result": _("Authorization Error. Insufficent permissions for '%s'") % e }
    except MKException, e:
        response = { "result_code": 1, "result": _("Check_MK exception: %s") % e }
    except Exception, e:
        if config.debug:
            raise
        log_exception()
        response = {
            "result_code" : 1,
            "result"      : _("Unhandled exception: %s") % traceback.format_exc(),
        }

    if html.output_format == "json":
        html.write(json.dumps(response))
    else:
        html.write(repr(response))
