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

from cmk.gui.globals import html

# Global datastructure holding all attributes (in a defined order)
# as pairs of (attr, topic). Topic is the title under which the
# attribute is being displayed. All builtin attributes use the
# topic None. As long as only one topic is used, no topics will
# be displayed. They are useful if you have a great number of
# custom attributes.
# TODO: Cleanup this duplicated data structure into a single one.
_host_attributes = []

# Dictionary for quick access
_host_attribute = {}


def all_host_attributes():
    return _host_attributes


def attributes():
    return _host_attribute


# Declare attributes with this method
def declare_host_attribute(a,
                           show_in_table=True,
                           show_in_folder=True,
                           show_in_host_search=True,
                           topic=None,
                           show_in_form=True,
                           depends_on_tags=None,
                           depends_on_roles=None,
                           editable=True,
                           show_inherited_value=True,
                           may_edit=None,
                           from_config=False):
    if depends_on_tags is None:
        depends_on_tags = []

    if depends_on_roles is None:
        depends_on_roles = []

    _host_attributes.append((a, topic))
    _host_attribute[a.name()] = a
    a._show_in_table = show_in_table
    a._show_in_folder = show_in_folder
    a._show_in_host_search = show_in_host_search
    a._show_in_form = show_in_form
    a._show_inherited_value = show_inherited_value
    a._depends_on_tags = depends_on_tags
    a._depends_on_roles = depends_on_roles
    a._editable = editable
    a._from_config = from_config

    if may_edit:
        a.may_edit = may_edit


def undeclare_host_attribute(attrname):
    global _host_attributes

    if attrname in _host_attribute:
        attr = _host_attribute[attrname]
        del _host_attribute[attrname]
        _host_attributes = [ha for ha in _host_attributes if ha[0].name() != attr.name()]


def undeclare_host_tag_attribute(tag_id):
    attrname = "tag_" + tag_id
    undeclare_host_attribute(attrname)


def host_attribute(name):
    return _host_attribute[name]


# Read attributes from HTML variables
def collect_attributes(for_what, do_validate=True, varprefix=""):
    host = {}
    for attr, _topic in all_host_attributes():
        attrname = attr.name()
        if not html.request.var(for_what + "_change_%s" % attrname, False):
            continue

        value = attr.from_html_vars(varprefix)

        if do_validate and attr.needs_validation(for_what):
            attr.validate_input(value, varprefix)

        host[attrname] = value
    return host
