#!/usr/bin/python
# -*- encoding: utf-8 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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
from pprint import pformat


def dump_environ_app(environ, start_response):
    dumped_env = "\n".join(["{0}: {1}".format(k, environ[k]) for k in environ.keys()])
    return serve_string(dumped_env)(environ, start_response)


def serve_string(_str):
    def _server(environ, start_response):
        status = '200 OK'
        response_headers = [('Content-Type', 'text/plain'), ('Content-Length', str(len(_str)))]
        start_response(status, response_headers)

        return [_str]

    return _server


def test_formdata(environ, start_response):
    # show the environment:
    output = [
        '<pre>',
        pformat(environ),
        '</pre>',
        '<form method="post">',
        '<input type="text" name="test">',
        '<input type="submit">',
        '</form>',
    ]

    if environ['REQUEST_METHOD'] == 'POST':
        # show form data as received by POST:
        output.append('<h1>FORM DATA</h1>')
        output.append(pformat(environ['wsgi.input'].read()))

    # send results
    output_len = sum(len(line) for line in output)
    start_response('200 OK', [('Content-type', 'text/html'), ('Content-Length', str(output_len))])
    return output
