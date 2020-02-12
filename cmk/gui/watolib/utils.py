#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import re
import pprint
import base64
import pickle
import six

import cmk
import cmk.utils.paths
import cmk.utils.rulesets.tuple_rulesets

import cmk.gui.config as config
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException

# TODO: Clean up all call sites in the GUI and only use them in WATO config file loading code
ALL_HOSTS = cmk.utils.rulesets.tuple_rulesets.ALL_HOSTS
ALL_SERVICES = cmk.utils.rulesets.tuple_rulesets.ALL_SERVICES
NEGATE = cmk.utils.rulesets.tuple_rulesets.NEGATE


def wato_root_dir():
    return cmk.utils.paths.check_mk_config_dir + "/wato/"


def multisite_dir():
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


# TODO: Move this to CEE specific code again
def liveproxyd_config_dir():
    return cmk.utils.paths.default_config_dir + "/liveproxyd.d/wato/"


# TODO: Find a better place later
def rename_host_in_list(thelist, oldname, newname):
    did_rename = False
    for nr, element in enumerate(thelist):
        if element == oldname:
            thelist[nr] = newname
            did_rename = True
        elif element == '!' + oldname:
            thelist[nr] = '!' + newname
            did_rename = True
    return did_rename


# Convert old tuple representation to new dict representation of
# folder's group settings
# TODO: Find a better place later
def convert_cgroups_from_tuple(value):
    if isinstance(value, dict):
        if "use_for_services" in value:
            return value

        new_value = {
            "use_for_services": False,
        }
        new_value.update(value)
        return value

    return {
        "groups": value[1],
        "recurse_perms": False,
        "use": value[0],
        "use_for_services": False,
        "recurse_use": False,
    }


# TODO: Find a better place later
def host_attribute_matches(crit, value):
    if crit and crit[0] == "~":
        # insensitive infix regex match
        return re.search(crit[1:], value, re.IGNORECASE) is not None

    # insensitive infix search
    return crit.lower() in value.lower()


# Returns the ID of the default site. This is the site the main folder has
# configured by default. It inherits to all folders and hosts which don't have
# a site set on their own.
# In standalone and master sites this defaults to the local site. In distributed
# slave sites, we don't know the site ID of the master site. We set this explicit
# to false to configure that this host is monitored by another site (that we don't
# know about).
# TODO: Find a better place later
def default_site():
    if config.is_wato_slave_site():
        return False
    return config.default_site()


def format_config_value(value):
    format_func = pprint.pformat if config.wato_pprint_config else repr
    return format_func(value)


def mk_repr(s):
    if not config.wato_legacy_eval:
        return base64.b64encode(six.ensure_binary(repr(s)))
    return base64.b64encode(pickle.dumps(s))


# TODO: Deprecate this legacy format with 1.4.0 or later?!
def mk_eval(s):
    try:
        if not config.wato_legacy_eval:
            return ast.literal_eval(base64.b64decode(s))
        return pickle.loads(base64.b64decode(s))
    except Exception:
        raise MKGeneralException(_('Unable to parse provided data: %s') % html.render_text(repr(s)))


def has_agent_bakery():
    return not cmk.is_raw_edition()


def site_neutral_path(path):
    if path.startswith('/omd'):
        parts = path.split('/')
        parts[3] = '[SITE_ID]'
        return '/'.join(parts)
    return path
