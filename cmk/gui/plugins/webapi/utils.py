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

"""Module to hold shared code for module internals and the plugins"""

# TODO: More feature related splitting up would be better

import abc
import json
from hashlib import md5

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.plugin_registry
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.log import logger
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import Hostname

# TODO: refactor to plugin_registry
api_actions = {}


class APICallCollection(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_api_calls(self):
        raise NotImplementedError("This API collection does not register any API call")



class APICallCollectionRegistry(cmk.gui.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return APICallCollection


    def _register(self, plugin_class):
        self._entries[plugin_class.__name__] = plugin_class


api_call_collection_registry = APICallCollectionRegistry()

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

# TODO: Rename to validate_hostname to be in sync with other functions
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


def validate_request_keys(request, required_keys = None, optional_keys = None):
    if required_keys:
        missing = set(required_keys) - set(request.keys())
        if missing:
            raise MKUserError(None, _("Missing required key(s): %s") % ", ".join(missing))


    all_keys = (required_keys or []) + (optional_keys or [])
    for key in request.keys():
        if key not in all_keys:
            raise MKUserError(None, _("Invalid key: %s") % key)


def validate_config_hash(hash_value, entity):
    entity_hash = compute_config_hash(entity)
    if hash_value != entity_hash:
        raise MKUserError(None, _("The configuration has changed in the meantime. "\
                                  "You need to load the configuration and start another update. "
                                  "If the existing configuration should not be checked, you can "
                                  "remove the configuration_hash value from the request object."))


def add_configuration_hash(response, configuration_object):
    response["configuration_hash"] = compute_config_hash(configuration_object)


def compute_config_hash(entity):
    try:
        entity_encoded = json.dumps(entity, sort_keys=True)
        entity_hash    = md5(entity_encoded).hexdigest()
    except Exception, e:
        logger.error("Error %s" % e)
        entity_hash = "0"

    return entity_hash


def validate_host_attributes(attributes):
    _validate_general_host_attributes(dict((key, value) for key, value in attributes.items() if not key.startswith("tag_")))
    _validate_host_tags(dict((key[4:], value) for key, value in attributes.items() if key.startswith("tag_")))


# Check if the given attribute name exists, no type check
def _validate_general_host_attributes(host_attributes):
    # inventory_failed and site are no "real" host_attributes (TODO: Clean this up!)
    all_host_attribute_names = [x.name() for x, _y in watolib.all_host_attributes()] + ["inventory_failed", "site"]
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
def _validate_host_tags(host_tags):
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
