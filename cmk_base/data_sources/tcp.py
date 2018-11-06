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

import socket

import cmk.debug
from cmk.exceptions import MKTerminate, MKGeneralException

import cmk_base.utils as utils
import cmk_base.config as config
from cmk_base.exceptions import MKAgentError, MKEmptyAgentData
from cmk_base.check_api_utils import state_markers

from .abstract import CheckMKAgentDataSource


def _normalize_ip_addresses(ip_addresses):
    '''factorize 10.0.0.{1,2,3}'''
    if not isinstance(ip_addresses, list):
        ip_addresses = ip_addresses.split()

    expanded = [word for word in ip_addresses if '{' not in word]
    for word in ip_addresses:
        if word in expanded:
            continue
        try:
            prefix, tmp = word.split('{')
            curly, suffix = tmp.split('}')
            expanded.extend(prefix + i + suffix for i in curly.split(','))
        except:
            raise MKGeneralException("could not expand %r" % word)
    return expanded


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

    def __init__(self, hostname, ipaddress):
        super(TCPDataSource, self).__init__(hostname, ipaddress)
        self._port = None
        self._timeout = None

    def id(self):
        return "agent"

    def set_port(self, port):
        self._port = port

    def _get_port(self):
        if self._port is not None:
            return self._port

        return config.agent_port_of(self._hostname)

    def set_timeout(self, timeout):
        self._timeout = timeout

    def _get_timeout(self):
        if self._timeout:
            return self._timeout

        return config.tcp_connect_timeout_of(self._hostname)

    def _execute(self):
        if self._use_only_cache:
            raise MKAgentError(
                "Got no data: No usable cache file present at %s" % self._cache_file_path())

        self._verify_ipaddress()

        port = self._get_port()

        encryption_settings = config.agent_encryption_of(self._hostname)

        socktype = (socket.AF_INET6 if config.is_ipv6_primary(self._hostname) else socket.AF_INET)
        s = socket.socket(socktype, socket.SOCK_STREAM)

        timeout = self._get_timeout()

        output = []
        self._logger.debug(
            "Connecting via TCP to %s:%d (%ss timeout)" % (self._ipaddress, port, timeout))
        try:
            s.settimeout(timeout)
            s.connect((self._ipaddress, port))
            s.settimeout(None)

            self._logger.debug("Reading data from agent")

            while True:
                data = s.recv(4096, socket.MSG_WAITALL)

                if data and len(data) > 0:
                    output.append(data)
                else:
                    break
        except MKTerminate:
            raise

        except socket.error, e:
            if cmk.debug.enabled():
                raise
            raise MKAgentError("Communication failed: %s" % e)
        finally:
            s.close()
        output = ''.join(output)

        if len(output) == 0:  # may be caused by xinetd not allowing our address
            raise MKEmptyAgentData("Empty output from agent at TCP port %d" % port)

        elif len(output) < 16:
            raise MKAgentError("Too short output from agent: %r" % output)

        output_is_plaintext = output.startswith("<<<")
        if encryption_settings["use_regular"] == "enforce" and output_is_plaintext:
            raise MKAgentError(
                "Agent output is plaintext but encryption is enforced by configuration")

        if not output_is_plaintext and encryption_settings["use_regular"] in ["enforce", "allow"]:
            try:
                # simply check if the protocol is an actual number
                int(output[0:2])

                output = self._decrypt_package(output[2:], encryption_settings["passphrase"])
            except ValueError:
                raise MKAgentError("Unsupported protocol version: %s" % output[:2])
            except Exception, e:
                if encryption_settings["use_regular"] == "enforce":
                    raise MKAgentError("Failed to decrypt agent output: %s" % e)
                else:
                    # of course the package might indeed have been encrypted but
                    # in an incorrect format, but how would we find that out?
                    # In this case processing the output will fail
                    pass

        return output

    def _sub_result_version(self, agent_info):
        agent_version = agent_info["version"]
        expected_version = config.agent_target_version(self._hostname)

        if expected_version and agent_version \
             and not self._is_expected_agent_version(agent_version, expected_version):
            # expected version can either be:
            # a) a single version string
            # b) a tuple of ("at_least", {'daily_build': '2014.06.01', 'release': '1.2.5i4'}
            #    (the dict keys are optional)
            if isinstance(expected_version, tuple) and expected_version[0] == 'at_least':
                expected = 'at least'
                if 'daily_build' in expected_version[1]:
                    expected += ' build %s' % expected_version[1]['daily_build']
                if 'release' in expected_version[1]:
                    if 'daily_build' in expected_version[1]:
                        expected += ' or'
                    expected += ' release %s' % expected_version[1]['release']
            else:
                expected = expected_version
            status = self._exit_code_spec.get("wrong_version", 1)
            output = ", unexpected agent version %s (should be %s)%s" \
                     % (agent_version, expected, state_markers[status])

        elif config.agent_min_version and agent_version < config.agent_min_version:
            status = self._exit_code_spec.get("wrong_version", 1)
            output = ", old plugin version %s (should be at least %s)%s" \
                     % (agent_version, config.agent_min_version, state_markers[status])

        else:
            status, output = 0, ''

        return status, output

    def _sub_result_only_from(self, agent_info):
        agent_only_from = agent_info.get("onlyfrom")

        ruleset = config.agent_config.get("only_from")
        if not ruleset:
            return 0, ''

        entries = config.host_extra_conf(self._hostname, ruleset)
        config_only_from = entries[0] if entries else None
        if None in (agent_only_from, config_only_from):
            return 0, ''

        allowed_nets = set(_normalize_ip_addresses(agent_only_from))
        expected_nets = set(_normalize_ip_addresses(config_only_from))
        if allowed_nets == expected_nets:
            return 0, ", allowed IP ranges: %s%s" \
                      % (" ".join(allowed_nets), state_markers[0])

        infotexts = []
        exceeding = allowed_nets - expected_nets
        if exceeding:
            infotexts.append("agent allows extra: %s" % " ".join(exceeding))
        missing = expected_nets - allowed_nets
        if missing:
            infotexts.append("agent blocks: %s" % " ".join(missing))

        return 1, ", invalid access configuration: %s%s" \
                  % (", ".join(infotexts), state_markers[1])

    def _summary_result(self):
        agent_info = self._get_agent_info()
        status, output, perfdata = super(TCPDataSource, self)._summary_result()

        for sub_status, sub_output in [
                self._sub_result_version(agent_info),
                self._sub_result_only_from(agent_info),
        ]:
            status = max(status, sub_status)
            output += ", %s" % sub_output

        return status, output, perfdata

    def _is_expected_agent_version(self, agent_version, expected_version):
        try:
            if agent_version in ['(unknown)', None, 'None']:
                return False

            if isinstance(expected_version, str) and expected_version != agent_version:
                return False

            elif isinstance(expected_version, tuple) and expected_version[0] == 'at_least':
                spec = expected_version[1]
                if utils.is_daily_build_version(agent_version) and 'daily_build' in spec:
                    expected = int(spec['daily_build'].replace('.', ''))

                    branch = utils.branch_of_daily_build(agent_version)
                    if branch == "master":
                        agent = int(agent_version.replace('.', ''))

                    else:  # branch build (e.g. 1.2.4-2014.06.01)
                        agent = int(agent_version.split('-')[1].replace('.', ''))

                    if agent < expected:
                        return False

                elif 'release' in spec:
                    if utils.is_daily_build_version(agent_version):
                        return False

                    if utils.parse_check_mk_version(agent_version) \
                        < utils.parse_check_mk_version(spec['release']):
                        return False

            return True
        except Exception, e:
            if cmk.debug.enabled():
                raise
            raise MKGeneralException(
                "Unable to check agent version (Agent: %s Expected: %s, Error: %s)" %
                (agent_version, expected_version, e))

    def _decrypt_package(self, encrypted_pkg, encryption_key):
        from Cryptodome.Cipher import AES
        from hashlib import md5

        unpad = lambda s: s[0:-ord(s[-1])]

        # Adapt OpenSSL handling of key and iv
        def derive_key_and_iv(password, key_length, iv_length):
            d = d_i = ''
            while len(d) < key_length + iv_length:
                d_i = md5(d_i + password).digest()
                d += d_i
            return d[:key_length], d[key_length:key_length + iv_length]

        key, iv = derive_key_and_iv(encryption_key, 32, AES.block_size)
        decryption_suite = AES.new(key, AES.MODE_CBC, iv)
        decrypted_pkg = decryption_suite.decrypt(encrypted_pkg)

        # Strip of fill bytes of openssl
        return unpad(decrypted_pkg)

    def describe(self):
        """Return a short textual description of the agent"""
        return "TCP: %s:%d" % (self._ipaddress, config.agent_port_of(self._hostname))

    @classmethod
    def use_only_cache(cls):
        cls._use_only_cache = True
