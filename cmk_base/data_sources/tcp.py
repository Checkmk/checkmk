#!/usr/bin/env python
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

import os
import signal
import socket
import subprocess

import cmk_base.console as console
import cmk_base.config as config
import cmk_base.checks as checks
from cmk_base.exceptions import MKAgentError

from .abstract import DataSource, CheckMKAgentDataSource


#.
#   .--Agent---------------------------------------------------------------.
#   |                        _                    _                        |
#   |                       / \   __ _  ___ _ __ | |_                      |
#   |                      / _ \ / _` |/ _ \ '_ \| __|                     |
#   |                     / ___ \ (_| |  __/ | | | |_                      |
#   |                    /_/   \_\__, |\___|_| |_|\__|                     |
#   |                            |___/                                     |
#   +----------------------------------------------------------------------+
#   | Real communication with the target system.                           |
#   '----------------------------------------------------------------------'

class TCPDataSource(CheckMKAgentDataSource):
    _use_only_cache = False

    def __init__(self):
        super(TCPDataSource, self).__init__()
        self._port = None


    def id(self):
        return "agent"


    def set_port(self, port):
        self._port = port


    def _get_port(self, hostname):
        if self._port is not None:
            return self._port
        else:
            return config.agent_port_of(hostname)


    def _execute(self, hostname, ipaddress):
        if self._use_only_cache:
            raise MKAgentError("Host is unreachable, no usable cache file present")

        self._verify_ipaddress(ipaddress)

        port = self._get_port(hostname)

        encryption_settings = config.agent_encryption_of(hostname)

        s = socket.socket(config.is_ipv6_primary(hostname) and socket.AF_INET6 or socket.AF_INET,
                          socket.SOCK_STREAM)
        s.settimeout(config.tcp_connect_timeout)

        console.vverbose("Connecting via TCP to %s:%d.\n" % (ipaddress, port))
        s.connect((ipaddress, port))
        # Immediately close sending direction. We do not send any data
        # s.shutdown(socket.SHUT_WR)
        try:
            s.setblocking(1)
        except:
            pass
        output = ""
        try:
            while True:
                out = s.recv(4096, socket.MSG_WAITALL)
                if out and len(out) > 0:
                    output += out
                else:
                    break
        except Exception, e:
            # Python seems to skip closing the socket under certain
            # conditions, leaving open filedescriptors and sockets in
            # CLOSE_WAIT. This happens one a timeout (ALERT signal)
            s.close()
            raise

        s.close()

        if len(output) == 0: # may be caused by xinetd not allowing our address
            raise MKAgentError("Empty output from agent at TCP port %d" % port)

        elif len(output) < 16:
            raise MKAgentError("Too short output from agent: %r" % output)

        if encryption_settings["use_regular"] == "enforce" and \
           output.startswith("<<<check_mk>>>"):
            raise MKAgentError("Agent output is plaintext but encryption is enforced by configuration")

        if encryption_settings["use_regular"] != "disabled":
            try:
                # currently ignoring version and timestamp
                #protocol_version = int(output[0:2])

                output = self._decrypt_package(output[2:], encryption_settings["passphrase"])
            except Exception, e:
                if encryption_settings["use_regular"] == "enforce":
                    raise MKAgentError("Failed to decrypt agent output: %s" % e)
                else:
                    # of course the package might indeed have been encrypted but
                    # in an incorrect format, but how would we find that out?
                    # In this case processing the output will fail
                    pass

        return output


    def _decrypt_package(self, encrypted_pkg, encryption_key):
        from Crypto.Cipher import AES
        from hashlib import md5

        unpad = lambda s : s[0:-ord(s[-1])]

        # Adapt OpenSSL handling of key and iv
        def derive_key_and_iv(password, key_length, iv_length):
            d = d_i = ''
            while len(d) < key_length + iv_length:
                d_i = md5(d_i + password).digest()
                d += d_i
            return d[:key_length], d[key_length:key_length+iv_length]

        key, iv = derive_key_and_iv(encryption_key, 32, AES.block_size)
        decryption_suite = AES.new(key, AES.MODE_CBC, iv)
        decrypted_pkg = decryption_suite.decrypt(encrypted_pkg)

        # Strip of fill bytes of openssl
        return unpad(decrypted_pkg)


    def name(self, hostname, ipaddress):
        """Return a unique (per host) textual identification of the data source"""
        return "%s:%d" % (ipaddress, config.agent_port_of(hostname))


    def describe(self, hostname, ipaddress):
        """Return a short textual description of the agent"""
        return "TCP: %s:%d" % (ipaddress, config.agent_port_of(hostname))


    @classmethod
    def use_only_cache(cls):
        cls._use_only_cache = True
