# -*- coding: utf-8 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
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

try:
    # First try python3
    # suppress missing import error from mypy
    from html import escape as html_escape  # type: ignore
except ImportError:
    # Default to python2
    from cgi import escape as html_escape


# There is common code with cmk/gui/view_utils:format_plugin_output(). Please check
# whether or not that function needs to be changed too
# TODO(lm): Find a common place to unify this functionality.
def format_plugin_output(output):
    ok_marker = '<b class="stmarkOK">OK</b>'
    warn_marker = '<b class="stmarkWARNING">WARN</b>'
    crit_marker = '<b class="stmarkCRITICAL">CRIT</b>'
    unknown_marker = '<b class="stmarkUNKNOWN">UNKN</b>'

    output = output.replace("(!)", warn_marker) \
              .replace("(!!)", crit_marker) \
              .replace("(?)", unknown_marker) \
              .replace("(.)", ok_marker)

    return output


def html_escape_context(context):
    unescaped_variables = {
        'PARAMETER_INSERT_HTML_SECTION',
        'PARAMETER_BULK_SUBJECT',
        'PARAMETER_HOST_SUBJECT',
        'PARAMETER_SERVICE_SUBJECT',
        'PARAMETER_FROM',
        'PARAMETER_REPLY_TO',
    }
    for variable, value in context.iteritems():
        if variable not in unescaped_variables:
            context[variable] = html_escape(value)


def add_debug_output(template, context):
    ascii_output = ""
    html_output = "<table class=context>\n"
    elements = context.items()
    elements.sort()
    for varname, value in elements:
        ascii_output += "%s=%s\n" % (varname, value)
        html_output += "<tr><td class=varname>%s</td><td class=value>%s</td></tr>\n" % (
            varname, html_escape(value))
    html_output += "</table>\n"
    return template.replace("$CONTEXT_ASCII$", ascii_output).replace("$CONTEXT_HTML$", html_output)
