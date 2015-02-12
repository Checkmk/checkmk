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

from lib import *
from wato import API
import config

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

api_actions = {}
loaded_with_language = False

def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
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

g_api = None

def page_api():
    global g_api

    try:
        if not config.user.get("automation_secret"):
            raise MKAuthException("The WATO API is only available for automation users")

        config.need_permission("wato.use")
        config.need_permission("wato.api_allowed")

        action = html.var('action')
        if action not in api_actions:
            raise MKUserError(None, "Unknown API action %s" % html.attrencode(action))

        # Create API instance
        g_api = API()

        # Prepare request_object
        # Most of the time the request is given as json
        # However, the plugin may have an own mechanism to interpret the request
        request_object = {}
        if html.var("request"):
            if api_actions[action].get("dont_eval_request"):
                request_object = html.var("request")
            else:
                eval_function = None
                request = html.var("request")

                try:
                    import json
                    eval_function = json.loads
                except ImportError:
                    eval_function = literal_eval
                    # modify request so it can be read by literal_eval...
                    for old, new in [ (": null",  ": None"),
                                      (": true",  ": True"),
                                      (": false", ": False"), ]:
                        request = request.replace(old, new)
                request_object = eval_function(request)
        else:
            request_object = {}

        if api_actions[action].get("locking", True):
            g_api.lock_wato()


        action_response = api_actions[action]["handler"](request_object)
        response = { "result_code": 0, "result": action_response }
    except Exception, e:
        response = { "result_code": 1, "result": str(e) }

    output_format = html.var("output_format", "json")
    if output_format == "json":
        # TODO: implement json alternative for python < 2.5
        import json
        html.write(json.dumps(response))
    else:
        html.write(repr(response))

