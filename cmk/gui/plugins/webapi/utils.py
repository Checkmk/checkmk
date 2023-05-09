#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for module internals and the plugins"""

# TODO: More feature related splitting up would be better

import abc
from hashlib import md5
import json
from typing import Type

from six import ensure_binary

import cmk.utils.plugin_registry

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.escaping as escaping
from cmk.gui.watolib.host_attributes import host_attribute_registry
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import Hostname


class APICallCollection(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_api_calls(self):
        raise NotImplementedError("This API collection does not register any API call")


class APICallCollectionRegistry(cmk.utils.plugin_registry.Registry[Type[APICallCollection]]):
    def plugin_name(self, instance):
        return instance.__name__


api_call_collection_registry = APICallCollectionRegistry()

#.
#   .--API Helpers---------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
# TODO: encapsulate in module/class


# TODO: Rename to validate_hostname to be in sync with other functions
def check_hostname(hostname, should_exist=True):
    # Validate hostname with valuespec
    Hostname().validate_value(hostname, "hostname")

    if should_exist:
        host = watolib.Host.host(hostname)
        if not host:
            raise MKUserError(None, _("No such host"))
    else:
        if (host := watolib.Host.host(hostname)) is not None:
            raise MKUserError(
                None,
                _("Host %s already exists in the folder %s") % (hostname, host.folder().path()))


def validate_config_hash(hash_value, entity):
    entity_hash = compute_config_hash(entity)
    if hash_value != entity_hash:
        raise MKUserError(
            None,
            _("The configuration has changed in the meantime. "
              "You need to load the configuration and start another update. "
              "If the existing configuration should not be checked, you can "
              "remove the configuration_hash value from the request object."))


def add_configuration_hash(response, configuration_object):
    response["configuration_hash"] = compute_config_hash(configuration_object)


def compute_config_hash(entity):
    try:
        entity_encoded = json.dumps(entity, sort_keys=True)
        entity_hash = md5(ensure_binary(entity_encoded)).hexdigest()
    except Exception as e:
        logger.error("Error %s", e)
        entity_hash = "0"

    return entity_hash


def validate_host_attributes(attributes, new=False):
    _validate_general_host_attributes(
        dict((key, value) for key, value in attributes.items() if not key.startswith("tag_")), new)
    _validate_host_tags(
        dict((key[4:], value) for key, value in attributes.items() if key.startswith("tag_")))


# Check if the given attribute name exists, no type check
def _validate_general_host_attributes(host_attributes, new):
    # inventory_failed and site are no "real" host_attributes (TODO: Clean this up!)
    all_host_attribute_names = list(host_attribute_registry.keys()) + ["inventory_failed", "site"]
    for name, value in host_attributes.items():
        if name not in all_host_attribute_names:
            raise MKUserError(None, _("Unknown attribute: %s") % escaping.escape_attribute(name))

        # For real host attributes validate the values
        try:
            attr = watolib.host_attribute(name)
        except KeyError:
            attr = None

        if attr is not None:
            if attr.needs_validation("host", new):
                attr.validate_input(value, "")

        # The site attribute gets an extra check
        if name == "site" and value not in config.allsites().keys():
            raise MKUserError(None, _("Unknown site %s") % escaping.escape_attribute(value))


# Check if the tag group exists and the tag value is valid
def _validate_host_tags(host_tags):
    for tag_group_id, tag_id in host_tags.items():
        for tag_group in config.tags.tag_groups:
            if tag_group.id == tag_group_id:
                for grouped_tag in tag_group.tags:
                    if grouped_tag.id == tag_id:
                        break
                else:
                    raise MKUserError(None, _("Unknown tag %s") % escaping.escape_attribute(tag_id))
                break
        else:
            raise MKUserError(None,
                              _("Unknown tag group %s") % escaping.escape_attribute(tag_group_id))
