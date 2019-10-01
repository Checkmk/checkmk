#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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

# small mock server simulating a jolokia server. Not very sophisticated
# but enough to get several checks to display something

from __future__ import print_function
import SocketServer
import SimpleHTTPServer
import urlparse

PORT = 8080


class FakeHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsedParams = urlparse.urlparse(self.path)
        params = [par for par in parsedParams.path.split('/') if par]

        print(params)

        self.send_response(200)
        self.send_header('Content-Type', 'application/xml')
        self.end_headers()

        if len(params) > 1:
            self.wfile.write('{"value": 1}')
        else:
            self.wfile.write('{"value": {"info":'\
                 '{"version": "1.0", "product": "Fake_Product"}, "agent": "Fake_Agent"}}')

        self.wfile.close()


class FakeTCPServer(SocketServer.TCPServer):
    allow_reuse_address = True


httpd = FakeTCPServer(("", 8080), FakeHandler)
httpd.serve_forever()
