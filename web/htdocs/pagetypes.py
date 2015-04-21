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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

class PageType:
    def __init__(self, d):
        self._ = d

    # Functions that subclasses *must* define
    # def type_name():
    #    return "foobar"

    # Object methods
    def topic(self):
        return self._["topic"]

    def title(self):
        return self._["title"]

    def description(self):
        return self._.get("description", "")

    def is_hidden(self):
        return self._.get("hidden", False)
    

    # Class variables and methods
    def builtin_pages():
        return {}


    __pages = {}

    # Lädt alle Dinge vom aktuellen User-Homeverzeichnis und
    # mergt diese mit den übergebenen eingebauten
    @classmethod
    def load():
        __pages.clear()

        # First load builtins from argument. Set username to ''
        for name, page in builtin_pages().items():
            page["owner"]  = '' # might have been forgotten on copy action
            page["public"] = True
            page["name"]   = name
            __pages[('', name)] = page

        # Now scan users subdirs for files "user_$type_name.mk"
        subdirs = os.listdir(config.config_dir)
        for user in subdirs:
            try:
                path = "%s/%s/user_%ss.mk" % (config.config_dir, user, type_name())
                if not os.path.exists(path):
                    continue

                user_pages = eval(file(path).read())
                for name, page in user_pages.items():
                    page["owner"] = user
                    page["name"] = name
                    __pages[(user, name)] = page

            except SyntaxError, e:
                raise MKGeneralException(_("Cannot load %s from %s: %s") % (what, path, e))

        # Declare custom permissions
        for page in __pages.values():
            declare_permission(page)


    def declare_permission(page):
        permname = "%s.%s" % (type_name(), page["name"])
        if page["public"] and not config.permission_exists(permname):
           config.declare_permission(permname, page["title"],
                             page["description"], ['admin','user','guest'])

page_types = {}

def declare_page_type(page_type):
    page_types[page_type.type_name()] = page_type

def load_user_pages():
    for page_type in page_types.values():
        page_type.load()

# -----------------------------------------------------------------------------------


class GraphCollection(PageType):
    def __init__(self, d):
        PageType.__init__(self, d)

    @classmethod
    def type_name():
        return "graph_collection"

declare_page_type(GraphCollection)

def page_foo():
    load_user_pages()
    html.write("HALLO")

