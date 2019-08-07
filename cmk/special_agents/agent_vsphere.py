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
import requests
import urllib3  # type: ignore


class ESXSession(requests.Session):
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

    def __init__(self, address, port, no_cert_check=False):
        super(ESXSession, self).__init__()
        if no_cert_check:
            self.verify = False
            urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)

        self._post_url = "https://%s:%s/sdk" % (address, port)
        self.headers.update({
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": "urn:vim25/5.0",
            "User-Agent": "Checkmk special agent vsphere",
        })

    def postsoap(self, request):
        soapdata = ESXSession.ENVELOPE % request
        return super(ESXSession, self).post(self._post_url, data=soapdata)
