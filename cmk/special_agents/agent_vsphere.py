#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
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
import sys
import httplib

from cmk.utils.exceptions import MKGeneralException


class ESXSession(object):
    """Encapsulates the Sessions with the ESX system"""
    ENVELOPE = ('<SOAP-ENV:Envelope'
                ' xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"'
                ' xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"'
                ' xmlns:ZSI="http://www.zolera.com/schemas/ZSI/"'
                ' xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/"'
                ' xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
                ' xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
                ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                '<SOAP-ENV:Header></SOAP-ENV:Header>'
                '<SOAP-ENV:Body xmlns:ns1="urn:vim25">%s</SOAP-ENV:Body>'
                '</SOAP-ENV:Envelope>')

    @staticmethod
    def _connect_to_server(address, port, no_cert_check, debug):
        """Initialize server connection"""
        try:
            netloc = "%s:%s" % (address, port)

            if no_cert_check:
                try:
                    import ssl
                    server_handle = httplib.HTTPSConnection(
                        netloc, context=ssl._create_unverified_context())
                except Exception:
                    server_handle = httplib.HTTPSConnection(netloc)
            else:
                server_handle = httplib.HTTPSConnection(netloc)

            if debug:
                sys.stderr.write("Connecting to %s..." % netloc)
                sys.stderr.flush()

            server_handle.connect()
            return server_handle
        except Exception as exc:
            if debug:
                raise
            raise MKGeneralException("Cannot connect to vSphere Server. Please check the IP and"
                                     " SSL certificate (if applicable) and try again. This error"
                                     " is not related to the login credentials."
                                     " Error message: %r" % exc)

    def __init__(self, address, port, no_cert_check=False, debug=False):
        super(ESXSession, self).__init__()
        self._server_handle = self._connect_to_server(address, port, no_cert_check, debug)
        self.headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": "urn:vim25/5.0",
            "User-Agent": "VMware VI Client/5.0.0",  # TODO: set client version?
        }

    def post(self, request):
        soapdata = ESXSession.ENVELOPE % request
        self._init_headers(soapdata)
        self._server_handle.send(soapdata)
        return self._server_handle.getresponse()

    def _init_headers(self, soapdata):
        self._server_handle.putrequest("POST", "/sdk")
        self._server_handle.putheader("Content-Length", "%d" % len(soapdata))
        for key, value in self.headers.iteritems():
            self._server_handle.putheader(key, value)
        self._server_handle.endheaders()
