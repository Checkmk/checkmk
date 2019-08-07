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

# TODO: Refactor/document locking. It is not clear when and how to apply
# locks or when they are held by which component.

# TODO: Refactor events to be handled as objects, e.g. in case when
# creating objects. Or at least update the documentation. It is not clear
# which fields are mandatory for the events.

import abc
import ast
import errno
import json
import os
import pathlib2 as pathlib
import pprint
import re
import select
import signal
import socket
import string
import subprocess
import sys
import threading
import time
import traceback

# Needed for receiving traps
from pysnmp import debug as snmp_debug
from pysnmp.proto import errind as snmp_errind
from pysnmp.entity import engine as snmp_engine
from pysnmp.entity import config as snmp_config
from pysnmp.entity.rfc3413 import ntfrcv as snmp_ntfrcv
from pysnmp.proto.api import v2c as snmp_v2c, v1 as snmp_v1

# Needed for trap translation
from pysnmp.smi.builder import MibBuilder, DirMibSource
from pysnmp.smi.view import MibViewController
from pysnmp.smi.rfc1902 import ObjectType, ObjectIdentity
from pysnmp.smi.error import SmiError
from pyasn1.error import ValueConstraintError

import cmk
import cmk.daemon
import cmk.defines as defines
import cmk.ec.export
import cmk.ec.settings
import cmk.log
import cmk.paths
import cmk.profile
import cmk.render
import livestatus
import cmk.regex

logger = cmk.log.get_logger("mkeventd")

#   .--Declarations--------------------------------------------------------.
#   |       ____            _                 _   _                        |
#   |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
#   |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
#   |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Global declarations and defaults settings                           |
#   '----------------------------------------------------------------------'

# Basic settings, can be changed with configuration file (at
# least I hope so)

syslog_priorities = ["emerg", "alert", "crit", "err", "warning", "notice", "info", "debug"]
syslog_facilities = ["kern", "user", "mail", "daemon", "auth", "syslog", "lpr", "news",
                     "uucp", "cron", "authpriv", "ftp",
                     "(unused 12)", "(unused 13)", "(unused 13)", "(unused 14)",
                     "local0", "local1", "local2", "local3", "local4", "local5", "local6", "local7",
                     None, None, None, None, None, None, None, "snmptrap"]

# Be aware: The order here is important. It must match the order of the fields
# in the history file entries (See get_event_history_from_file). The fields in
# the file are currectly in the same order as StatusTableHistory.columns.
#
# Please note: Keep this in sync with livestatus/src/TableEventConsole.cc.
grepping_filters = [
    'event_id',
    'event_text',
    'event_comment',
    'event_host',
    'event_host_regex',
    'event_contact',
    'event_application',
    'event_rule_id',
    'event_owner',
    'event_ipaddress',
    'event_core_host',
]


# Alas, we often have no clue about the actual encoding, so we have to guess:
# Initially we assume UTF-8, but fall back to latin-1 if it didn't work.
def decode_from_bytes(string_as_bytes):
    # This is just a safeguard if we are inadvertedly called with a Unicode
    # string. In theory this should never happen, but given the typing chaos in
    # this script, one never knows. In the Unicode case, Python tries to be
    # "helpful", but this fails miserably: Calling 'decode' on a Unicode string
    # implicitly converts it via 'encode("ascii")' to a byte string first, but
    # this can of course fail and doesn't make sense at all when we immediately
    # call 'decode' on this byte string again. In a nutshell: The implicit
    # conversions between str and unicode are a fundamentally broken idea, just
    # like all implicit things and "helpful" ideas in general. :-P For further
    # info see e.g. http://nedbatchelder.com/text/unipain.html
    if type(string_as_bytes) == unicode:
        return string_as_bytes

    try:
        return string_as_bytes.decode("utf-8")
    except Exception:
        return string_as_bytes.decode("latin-1")


# Rip out/replace any characters which have a special meaning in the UTF-8
# encoded history files, see e.g. quote_tab. In theory this shouldn't be
# necessary, because there are a bunch of bytes which are not contained in any
# valid UTF-8 string, but following Murphy's Law, those are not used in
# Check_MK. To keep backwards compatibility with old history files, we have no
# choice and continue to do it wrong... :-/
def scrub_string(s):
    if type(s) == str:
        return s.translate(scrub_string.str_table, "\0\1\2\n")
    if type(s) == unicode:
        return s.translate(scrub_string.unicode_table)
    raise TypeError("scrub_string expects a string argument")


scrub_string.str_table = string.maketrans("\t", " ")
scrub_string.unicode_table = {
    0: None,
    1: None,
    2: None,
    ord("\n"): None,
    ord("\t"): ord(" ")
}


def scrub_and_decode(s):
    return decode_from_bytes(scrub_string(s))


def unsplit(s):
    if not isinstance(s, basestring):
        return s

    elif s.startswith('\2'):
        return None  # \2 is the designator for None

    elif s.startswith('\1'):
        if len(s) == 1:
            return ()
        else:
            return tuple(s[1:].split('\1'))
    else:
        return s


# Speed-critical function for converting string representation
# of log line back to Python values
def convert_history_line(values):
    # NOTE: history_line column is missing here, so indices are off by 1! :-P
    values[0] = float(values[0])         # history_time
    values[4] = int(values[4])           # event_id
    values[5] = int(values[5])           # event_count
    values[7] = float(values[7])         # event_first
    values[8] = float(values[8])         # event_last
    values[10] = int(values[10])         # event_sl
    values[14] = int(values[14])         # event_pid
    values[15] = int(values[15])         # event_priority
    values[16] = int(values[16])         # event_facility
    values[18] = int(values[18])         # event_state
    values[21] = unsplit(values[21])     # event_match_groups
    num_values = len(values)
    if num_values <= 22:                 # event_contact_groups
        values.append(None)
    else:
        values[22] = unsplit(values[22])
    if num_values <= 23:                 # event_ipaddress
        values.append(StatusTableHistory.columns[24][1])
    if num_values <= 24:                 # event_orig_host
        values.append(StatusTableHistory.columns[25][1])
    if num_values <= 25:                 # event_contact_groups_precedence
        values.append(StatusTableHistory.columns[26][1])
    if num_values <= 26:                 # event_core_host
        values.append(StatusTableHistory.columns[27][1])
    if num_values <= 27:                 # event_host_in_downtime
        values.append(StatusTableHistory.columns[28][1])
    else:
        values[27] = values[27] == "1"
    if num_values <= 28:                 # event_match_groups_syslog_application
        values.append(StatusTableHistory.columns[29][1])
    else:
        values[28] = unsplit(values[28])


filter_operators = {
    "=": (lambda a, b: a == b),
    ">": (lambda a, b: a > b),
    "<": (lambda a, b: a < b),
    ">=": (lambda a, b: a >= b),
    "<=": (lambda a, b: a <= b),
    "~": (lambda a, b: cmk.regex.regex(b).search(a)),
    "=~": (lambda a, b: a.lower() == b.lower()),
    "~~": (lambda a, b: cmk.regex.regex(b.lower()).search(a.lower())),
    "in": (lambda a, b: a in b),
}


#.
#   .--Helper functions----------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Various helper functions                                            |
#   '----------------------------------------------------------------------'

class ECLock(object):
    def __init__(self, ident):
        super(ECLock, self).__init__()
        self._lock = threading.Lock()
        self._logger = logger.getChild("lock.%s" % ident)

    def acquire(self, blocking=True):
        self._logger.debug("[%s] Trying to acquire lock", threading.current_thread().name)

        ret = self._lock.acquire(blocking)
        if ret is True:
            self._logger.debug("[%s] Acquired lock", threading.current_thread().name)
        else:
            self._logger.debug("[%s] Non-blocking aquire failed", threading.current_thread().name)

        return ret

    def release(self):
        self._logger.debug("[%s] Releasing lock", threading.current_thread().name)
        self._lock.release()

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False  # Do not swallow exceptions


class ECServerThread(threading.Thread):
    @abc.abstractmethod
    def serve(self):
        raise NotImplementedError()

    def __init__(self, name, settings, config, slave_status, table_events, profiling_enabled, profile_file):
        super(ECServerThread, self).__init__(name=name)
        self.settings = settings
        self._config = config
        self._slave_status = slave_status
        self._table_events = table_events
        self._profiling_enabled = profiling_enabled
        self._profile_file = profile_file
        self._terminate_event = threading.Event()
        self._logger = logger.getChild(name)

    def run(self):
        self._logger.info("Starting up")

        while not self._shal_terminate():
            try:
                with cmk.profile.Profile(enabled=self._profiling_enabled,
                                         profile_file=str(self._profile_file)):
                    self.serve()
            except Exception:
                self._logger.exception("Exception in %s server" % self.name)
                if self.settings.options.debug:
                    raise
                time.sleep(1)

        self._logger.info("Terminated")

    def _shal_terminate(self):
        return self._terminate_event.is_set()

    def terminate(self):
        self._terminate_event.set()


def terminate(terminate_main_event, event_server, status_server):
    terminate_main_event.set()
    status_server.terminate()
    event_server.terminate()


def bail_out(reason):
    logger.error("FATAL ERROR: %s" % reason)
    sys.exit(1)


def process_exists(pid):
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def drain_pipe(pipe):
    while True:
        try:
            readable = select.select([pipe], [], [], 0.1)[0]
        except select.error as e:
            if e[0] == errno.EINTR:
                continue
            raise

        data = None
        if pipe in readable:
            try:
                data = os.read(pipe, 4096)
                if len(data) == 0:  # END OF FILE!
                    break
            except Exception:
                break  # Error while reading
        else:
            break  # No data available


def match(pattern, text, complete=True):
    if pattern is None:
        return True
    elif type(pattern) in [str, unicode]:
        if complete:
            return pattern == text.lower()
        else:
            return pattern in text.lower()
    else:
        # Assume compiled regex
        m = pattern.search(text)
        if m:
            groups = m.groups()
            if None in groups:
                # Remove None from result tuples and replace it with empty strings
                return tuple([g if g is not None else ''
                              for g in groups])
            else:
                return groups
        else:
            return False


def pattern(pat):
    try:
        return pat.pattern
    except Exception:
        return pat


# Sorry: this code is dupliated in web/plugins/wato/mkeventd.py
def match_ipv4_network(pattern, ipaddress_text):
    network, network_bits = parse_ipv4_network(pattern)  # is validated by valuespec
    if network_bits == 0:
        return True  # event if ipaddress is empty
    try:
        ipaddress = parse_ipv4_address(ipaddress_text)
    except Exception:
        return False  # invalid address never matches

    # first network_bits of network and ipaddress must be
    # identical. Create a bitmask.
    bitmask = 0
    for n in xrange(32):
        bitmask = bitmask << 1
        if n < network_bits:
            bit = 1
        else:
            bit = 0
        bitmask += bit

    return (network & bitmask) == (ipaddress & bitmask)


def parse_ipv4_address(text):
    parts = map(int, text.split("."))
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]


def parse_ipv4_network(text):
    if "/" not in text:
        return parse_ipv4_address(text), 32

    network_text, bits_text = text.split("/")
    return parse_ipv4_address(network_text), int(bits_text)


def replace_groups(text, origtext, match_groups):
    # replace \0 with text itself. This allows to add information
    # in front or and the end of a message
    text = text.replace("\\0", origtext)

    # Generic replacement with \1, \2, ...
    match_groups_message = match_groups.get("match_groups_message")
    if type(match_groups_message) == tuple:
        for nr, g in enumerate(match_groups_message):
            text = text.replace("\\%d" % (nr + 1), g)

    # Replacement with keyword
    # Right now we have
    # $MATCH_GROUPS_MESSAGE_x$
    # $MATCH_GROUPS_SYSLOG_APPLICATION_x$
    for key_prefix, values in match_groups.iteritems():
        if type(values) != tuple:
            continue

        for idx, match in enumerate(values):
            text = text.replace("$%s_%d$" % (key_prefix.upper(), idx + 1), match)

    return text


class MKSignalException(Exception):
    def __init__(self, signum):
        Exception.__init__(self, "Got signal %d" % signum)
        self._signum = signum


def signal_handler(signum, stack_frame):
    logger.verbose("Got signal %d." % signum)
    raise MKSignalException(signum)


class MKClientError(Exception):
    def __init__(self, t):
        Exception.__init__(self, t)


#.
#   .--SNMP-Traps----------------------------------------------------------.
#   |        ____  _   _ __  __ ____     _____                             |
#   |       / ___|| \ | |  \/  |  _ \   |_   _| __ __ _ _ __  ___          |
#   |       \___ \|  \| | |\/| | |_) |____| || '__/ _` | '_ \/ __|         |
#   |        ___) | |\  | |  | |  __/_____| || | | (_| | |_) \__ \         |
#   |       |____/|_| \_|_|  |_|_|        |_||_|  \__,_| .__/|___/         |
#   |                                                  |_|                 |
#   +----------------------------------------------------------------------+
#   | Generic SNMP-Trap processing functions                               |
#   '----------------------------------------------------------------------'

def initialize_snmptrap_handling(settings, config, event_server, table_events):
    if settings.options.snmptrap_udp is None:
        return

    initialize_snmptrap_engine(config, event_server, table_events)

    if snmptrap_translation_enabled(config):
        event_server.load_mibs()


def initialize_snmptrap_engine(config, event_server, table_events):
    the_snmp_engine = snmp_engine.SnmpEngine()

    # Hand over our logger to PySNMP
    snmp_debug.setLogger(snmp_debug.Debug("all", printer=logger.getChild("snmp").debug))

    # Disable receiving of SNMPv3 INFORM messages. We do not support them (yet)
    class ECNotificationReceiver(snmp_ntfrcv.NotificationReceiver):
        pduTypes = (snmp_v1.TrapPDU.tagSet, snmp_v2c.SNMPv2TrapPDU.tagSet)

    initialize_snmp_credentials(config, the_snmp_engine)
    global g_snmp_receiver, g_snmp_engine
    g_snmp_receiver = ECNotificationReceiver(the_snmp_engine, event_server.handle_snmptrap)
    g_snmp_engine = the_snmp_engine

    g_snmp_engine.observer.registerObserver(event_server.handle_unauthenticated_snmptrap,
        "rfc2576.prepareDataElements:sm-failure", "rfc3412.prepareDataElements:sm-failure")


def auth_proto_for(proto_name):
    if proto_name == "md5":
        return snmp_config.usmHMACMD5AuthProtocol
    if proto_name == "sha":
        return snmp_config.usmHMACSHAAuthProtocol
    raise Exception("Invalid SNMP auth protocol: %s" % proto_name)


def priv_proto_for(proto_name):
    if proto_name == "DES":
        return snmp_config.usmDESPrivProtocol
    if proto_name == "AES":
        return snmp_config.usmAesCfb128Protocol
    raise Exception("Invalid SNMP priv protocol: %s" % proto_name)


def initialize_snmp_credentials(config, the_snmp_engine):
    user_num = 0
    for spec in config["snmp_credentials"]:
        credentials = spec["credentials"]
        user_num += 1

        # SNMPv1/v2
        if type(credentials) != tuple:
            community_index = 'snmpv2-%d' % user_num
            logger.info("adding SNMPv1 system: communityIndex=%s" % community_index)
            snmp_config.addV1System(the_snmp_engine, community_index, credentials)
            continue

        # SNMPv3
        securityLevel = credentials[0]
        if securityLevel == "noAuthNoPriv":
            user_id = credentials[1]
            auth_proto = snmp_config.usmNoAuthProtocol
            auth_key = None
            priv_proto = snmp_config.usmNoPrivProtocol
            priv_key = None
        elif securityLevel == "authNoPriv":
            user_id = credentials[2]
            auth_proto = auth_proto_for(credentials[1])
            auth_key = credentials[3]
            priv_proto = snmp_config.usmNoPrivProtocol
            priv_key = None
        elif securityLevel == "authPriv":
            user_id = credentials[2]
            auth_proto = auth_proto_for(credentials[1])
            auth_key = credentials[3]
            priv_proto = priv_proto_for(credentials[4])
            priv_key = credentials[5]
        else:
            raise Exception("Invalid SNMP security level: %s" % securityLevel)

        for engine_id in spec.get("engine_ids", []):
            logger.info("adding SNMPv3 user: userName=%s, authProtocol=%s, privProtocol=%s, securityEngineId=%s" %
                        (user_id,
                         ".".join(str(i) for i in auth_proto),
                         ".".join(str(i) for i in priv_proto),
                         engine_id))
            snmp_config.addV3User(
                the_snmp_engine, user_id,
                auth_proto, auth_key,
                priv_proto, priv_key,
                securityEngineId=snmp_v2c.OctetString(hexValue=engine_id))

#.
#   .--Timeperiods---------------------------------------------------------.
#   |      _____ _                                _           _            |
#   |     |_   _(_)_ __ ___   ___ _ __   ___ _ __(_) ___   __| |___        |
#   |       | | | | '_ ` _ \ / _ \ '_ \ / _ \ '__| |/ _ \ / _` / __|       |
#   |       | | | | | | | | |  __/ |_) |  __/ |  | | (_) | (_| \__ \       |
#   |       |_| |_|_| |_| |_|\___| .__/ \___|_|  |_|\___/ \__,_|___/       |
#   |                            |_|                                       |
#   +----------------------------------------------------------------------+
#   |  Timeperiods are used in rule conditions                             |
#   '----------------------------------------------------------------------'

# Dictionary from name to True/False (active / inactive)
g_timeperiods = None
g_last_timeperiod_update = 0


def update_timeperiods(settings):
    global g_timeperiods, g_last_timeperiod_update

    if g_timeperiods is not None and int(time.time()) / 60 == g_last_timeperiod_update:
        return  # only update once a minute
    try:
        table = livestatus.LocalConnection().query("GET timeperiods\nColumns: name alias in")
        new_timeperiods = {}
        for tpname, alias, isin in table:
            new_timeperiods[tpname] = (alias, bool(isin))
        g_timeperiods = new_timeperiods
        g_last_timeperiod_update = int(time.time()) / 60
    except Exception as e:
        logger.exception("Cannot update timeperiod information: %s" % e)
        if settings.options.debug:
            raise


def check_timeperiod(settings, tpname):
    update_timeperiods(settings)
    if not g_timeperiods:
        logger.warning("No timeperiod information. Assuming %s active" % tpname)
        return True

    elif tpname not in g_timeperiods:
        logger.warning("No such timeperiod %s. Assume to active" % tpname)
        return True

    else:
        return g_timeperiods[tpname][1]


#.
#   .--Host config---------------------------------------------------------.
#   |          _   _           _                      __ _                 |
#   |         | | | | ___  ___| |_    ___ ___  _ __  / _(_) __ _           |
#   |         | |_| |/ _ \/ __| __|  / __/ _ \| '_ \| |_| |/ _` |          |
#   |         |  _  | (_) \__ \ |_  | (_| (_) | | | |  _| | (_| |          |
#   |         |_| |_|\___/|___/\__|  \___\___/|_| |_|_| |_|\__, |          |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+
#   | Manages the configuration of the hosts of the local monitoring core. |
#   | It fetches and caches the information during runtine of the EC.      |
#   '----------------------------------------------------------------------'

class HostConfig(object):
    def __init__(self):
        self._logger = logger.getChild("HostConfig")
        self.initialize()

    def initialize(self):
        self._logger.debug("Initializing host config")
        self._event_host_to_host = {}

        self._hosts_by_name = {}
        self._hosts_by_lower_name = {}
        self._hosts_by_lower_alias = {}
        self._hosts_by_lower_address = {}

        self._got_config_from_core = False

    def get(self, host_name, deflt=None):
        return self._hosts_by_name.get(host_name, deflt)

    def get_by_event_host_name(self, event_host_name, deflt=None):
        try:
            self._update_from_core()
        except Exception:
            self._logger.exception("Failed to get host info from core. Try again later.")
            return

        try:
            return self._event_host_to_host[event_host_name]
        except KeyError:
            pass  # Not cached yet

        # Note: It is important that we use exactly the same algorithm here as in the core
        # (enterprise/core/src/World.cc getHostByDesignation)
        #
        # Host name    : Case insensitive equality (host_name =~ %s)
        # Host alias   : Case insensitive equality (host_alias =~ %s)
        # Host address : Case insensitive equality (host_address =~ %s)
        low_event_host_name = event_host_name.lower()

        host = deflt
        for search_map in [self._hosts_by_lower_name, self._hosts_by_lower_address,
                           self._hosts_by_lower_alias]:
            try:
                host = search_map[low_event_host_name]
                break
            except KeyError:
                continue

        self._event_host_to_host[event_host_name] = host
        return host

    def _update_from_core(self):
        if not self._has_core_config_reloaded():
            return

        self.initialize()
        self._logger.debug("Fetching host config from core")

        columns = [
            "name",
            "alias",
            "address",
            "custom_variables",
            "contacts",
            "contact_groups",
        ]

        query = "GET hosts\nColumns: %s" % " ".join(columns)
        for host in livestatus.LocalConnection().query_table_assoc(query):
            self._hosts_by_name[host["name"]] = host

            # Lookup maps to improve performance of host searches
            self._hosts_by_lower_name[host["name"].lower()] = host
            self._hosts_by_lower_alias[host["alias"].lower()] = host
            self._hosts_by_lower_address[host["address"].lower()] = host

        self._logger.debug("Got %d hosts from core" % len(self._hosts_by_name))
        self._got_config_from_core = self._get_core_start_time()

    def _has_core_config_reloaded(self):
        if not self._got_config_from_core:
            return True

        if self._get_core_start_time() > self._got_config_from_core:
            return True

        return False

    def _get_core_start_time(self):
        query = (
            "GET status\n"
            "Columns: program_start\n"
        )
        return livestatus.LocalConnection().query_value(query)


#.
#   .--MongoDB-------------------------------------------------------------.
#   |             __  __                         ____  ____                |
#   |            |  \/  | ___  _ __   __ _  ___ |  _ \| __ )               |
#   |            | |\/| |/ _ \| '_ \ / _` |/ _ \| | | |  _ \               |
#   |            | |  | | (_) | | | | (_| | (_) | |_| | |_) |              |
#   |            |_|  |_|\___/|_| |_|\__, |\___/|____/|____/               |
#   |                                |___/                                 |
#   +----------------------------------------------------------------------+
#   | The Event Log Archive can be stored in a MongoDB instead of files,   |
#   | this section contains MongoDB related code.                          |
#   '----------------------------------------------------------------------'

try:
    from pymongo.connection import Connection
    from pymongo import DESCENDING
    from pymongo.errors import OperationFailure
    import datetime
except ImportError:
    Connection = None

g_mongo_conn = None
g_mongo_db = None


def mongodb_local_connection_opts(settings):
    ip, port = None, None
    with settings.paths.mongodb_config_file.value.open(encoding='utf-8') as f:
        for l in f:
            if l.startswith('bind_ip'):
                ip = l.split('=')[1].strip()
            elif l.startswith('port'):
                port = int(l.split('=')[1].strip())
    return ip, port


def connect_mongodb(settings):
    global g_mongo_conn, g_mongo_db
    if Connection is None:
        raise Exception('Could not initialize MongoDB (Python-Modules are missing)')
    g_mongo_conn = Connection(*mongodb_local_connection_opts(settings))
    g_mongo_db = g_mongo_conn.__getitem__(os.environ['OMD_SITE'])


def flush_event_history_mongodb():
    g_mongo_db.ec_archive.drop()


def get_mongodb_max_history_age():
    result = g_mongo_db.ec_archive.index_information()
    if 'dt_-1' not in result or 'expireAfterSeconds' not in result['dt_-1']:
        return -1
    else:
        return result['dt_-1']['expireAfterSeconds']


def update_mongodb_indexes(settings):
    if not g_mongo_conn:
        connect_mongodb(settings)
    result = g_mongo_db.ec_archive.index_information()

    if 'time_-1' not in result:
        g_mongo_db.ec_archive.ensure_index([('time', DESCENDING)])


def update_mongodb_history_lifetime(settings, config):
    if not g_mongo_conn:
        connect_mongodb(settings)

    if get_mongodb_max_history_age() == config['history_lifetime'] * 86400:
        return  # do not update already correct index

    try:
        g_mongo_db.ec_archive.drop_index("dt_-1")
    except OperationFailure:
        pass  # Ignore not existing index

    # Delete messages after x days
    g_mongo_db.ec_archive.ensure_index(
        [('dt', DESCENDING)],
        expireAfterSeconds=config['history_lifetime'] * 86400,
        unique=False
    )


def mongodb_next_id(name, first_id=0):
    ret = g_mongo_db.counters.find_and_modify(
        query={'_id': name},
        update={'$inc': {'seq': 1}},
        new=True
    )

    if not ret:
        # Initialize the index!
        g_mongo_db.counters.insert({
            '_id': name,
            'seq': first_id
        })
        return first_id
    else:
        return ret['seq']


def log_event_history_to_mongodb(settings, event, what, who, addinfo):
    if not g_mongo_conn:
        connect_mongodb(settings)
    # We converted _id to be an auto incrementing integer. This makes the unique
    # index compatible to history_line of the file (which is handled as integer)
    # within mkeventd. It might be better to use the ObjectId() of MongoDB, but
    # for the first step, we use the integer index for simplicity
    now = time.time()
    g_mongo_db.ec_archive.insert({
        '_id': mongodb_next_id('ec_archive_id'),
        'dt': datetime.datetime.fromtimestamp(now),
        'time': now,
        'event': event,
        'what': what,
        'who': who,
        'addinfo': addinfo,
    })


def get_event_history_from_mongodb(settings, table_events, query):
    filters, limit = query.filters, query.limit

    history_entries = []

    if not g_mongo_conn:
        connect_mongodb(settings)

    # Construct the mongodb filtering specification. We could fetch all information
    # and do filtering on this data, but this would be way too inefficient.
    query = {}
    for filter_name, opfunc, args in filters:

        if opfunc == filter_operators['=']:
            mongo_filter = args
        elif opfunc == filter_operators['>']:
            mongo_filter = {'$gt': args}
        elif opfunc == filter_operators['<']:
            mongo_filter = {'$lt': args}
        elif opfunc == filter_operators['>=']:
            mongo_filter = {'$gte': args}
        elif opfunc == filter_operators['<=']:
            mongo_filter = {'$lte': args}
        elif opfunc == filter_operators['~']:  # case sensitive regex, find pattern in string
            mongo_filter = {'$regex': args, '$options': ''}
        elif opfunc == filter_operators['=~']:  # case insensitive, match whole string
            mongo_filter = {'$regex': args, '$options': 'mi'}
        elif opfunc == filter_operators['~~']:  # case insensitive regex, find pattern in string
            mongo_filter = {'$regex': args, '$options': 'i'}
        elif opfunc == filter_operators['in']:
            mongo_filter = {'$in': args}
        else:
            raise Exception('Filter operator of filter %s not implemented for MongoDB archive' % filter_name)

        if filter_name[:6] == 'event_':
            query['event.' + filter_name[6:]] = mongo_filter
        elif filter_name[:8] == 'history_':
            key = filter_name[8:]
            if key == 'line':
                key = '_id'
            query[key] = mongo_filter
        else:
            raise Exception('Filter %s not implemented for MongoDB' % filter_name)

    result = g_mongo_db.ec_archive.find(query).sort('time', -1)

    # Might be used for debugging / profiling
    #file(cmk.paths.omd_root + '/var/log/check_mk/ec_history_debug.log', 'a').write(
    #    pprint.pformat(filters) + '\n' + pprint.pformat(result.explain()) + '\n')

    if limit:
        result = result.limit(limit + 1)

    # now convert the MongoDB data structure to the eventd internal one
    for entry in result:
        item = [
            entry['_id'],
            entry['time'],
            entry['what'],
            entry['who'],
            entry['addinfo'],
        ]
        for colname, defval in table_events.columns:
            key = colname[6:]  # drop "event_"
            item.append(entry['event'].get(key, defval))
        history_entries.append(item)

    return history_entries


#.
#   .--History-------------------------------------------------------------.
#   |                   _   _ _     _                                      |
#   |                  | | | (_)___| |_ ___  _ __ _   _                    |
#   |                  | |_| | / __| __/ _ \| '__| | | |                   |
#   |                  |  _  | \__ \ || (_) | |  | |_| |                   |
#   |                  |_| |_|_|___/\__\___/|_|   \__, |                   |
#   |                                             |___/                    |
#   +----------------------------------------------------------------------+
#   | Functions for logging the history of events                          |
#   '----------------------------------------------------------------------'

def log_event_history(settings, config, table_events, event, what, who="", addinfo=""):
    if config["debug_rules"]:
        logger.info("Event %d: %s/%s/%s - %s" % (event["id"], what, who, addinfo, event["text"]))

    if config['archive_mode'] == 'mongodb':
        log_event_history_to_mongodb(settings, event, what, who, addinfo)
    else:
        log_event_history_to_file(settings, config, table_events, event, what, who, addinfo)


# Make a new entry in the event history. Each entry is tab-separated line
# with the following columns:
# 0: time of log entry
# 1: type of entry (keyword)
# 2: user who initiated the action (for GUI actions)
# 3: additional information about the action
# 4-oo: StatusTableEvents.columns
def log_event_history_to_file(settings, config, table_events, event, what, who, addinfo):
    with lock_logging:
        columns = [
            str(time.time()),
            scrub_string(what),
            scrub_string(who),
            scrub_string(addinfo)
        ]
        columns += [quote_tab(event.get(colname[6:], defval))  # drop "event_"
                    for colname, defval in table_events.columns]

        with get_logfile(config, settings.paths.history_dir.value).open(mode='ab') as f:
            f.write("\t".join(map(to_utf8, columns)) + "\n")


def to_utf8(x):
    if type(x) == unicode:
        return x.encode("utf-8")
    else:
        return x


def quote_tab(col):
    ty = type(col)
    if ty in [float, int]:
        return str(col)
    elif ty is bool:
        return col and "1" or "0"
    elif ty in [tuple, list]:
        col = "\1" + "\1".join([quote_tab(e) for e in col])
    elif col is None:
        col = "\2"
    elif ty is unicode:
        col = col.encode("utf-8")

    return col.replace("\t", " ")


active_history_period = None


# Get file object to current log file, handle also
# history and lifetime limit.
def get_logfile(config, log_dir):
    global active_history_period
    log_dir.mkdir(parents=True, exist_ok=True)
    # Log into file starting at current history period,
    # but: if a newer logfile exists, use that one. This
    # can happen if you switch the period from daily to
    # weekly.
    timestamp = current_history_period(config)

    # Log period has changed or we have not computed a filename yet ->
    # compute currently active period
    if active_history_period is None or timestamp > active_history_period:

        # Look if newer files exist
        timestamps = sorted(int(str(path.name)[:-4])
                            for path in log_dir.glob('*.log'))
        if len(timestamps) > 0:
            timestamp = max(timestamps[-1], timestamp)

        active_history_period = timestamp

    return log_dir / ("%d.log" % timestamp)


# Return timestamp of the beginning of the current history
# period.
def current_history_period(config):
    now_broken = list(time.localtime())
    now_broken[3:6] = [0, 0, 0]  # set clock to 00:00:00
    now_ts = time.mktime(now_broken)  # convert to timestamp
    if config["history_rotation"] == "weekly":
        now_ts -= now_broken[6] * 86400  # convert to monday
    return int(now_ts)


# Delete old log files
def expire_logfiles(settings, config, flush=False):
    try:
        days = config["history_lifetime"]
        min_mtime = time.time() - days * 86400
        logger.verbose("Expiring logfiles (Horizon: %d days -> %s)" %
                       (days, cmk.render.date_and_time(min_mtime)))
        for path in settings.paths.history_dir.value.glob('*.log'):
            if flush or path.stat().st_mtime < min_mtime:
                logger.info("Deleting log file %s (age %s)" %
                            (path, cmk.render.date_and_time(path.stat().st_mtime)))
                path.unlink()
    except Exception as e:
        if settings.options.debug:
            raise
        logger.exception("Error expiring log files: %s" % e)


def flush_event_history(settings, config):
    if config['archive_mode'] == 'mongodb':
        flush_event_history_mongodb()
    else:
        flush_event_history_files(settings, config)


def flush_event_history_files(settings, config):
    with lock_logging:
        expire_logfiles(settings, config, True)


def get_event_history_from_file(settings, table_history, status_logger, query):
    filters, limit = query.filters, query.limit
    history_entries = []
    if not settings.paths.history_dir.value.exists():
        return []

    status_logger.debug("Filters: %r", filters)
    status_logger.debug("Limit: %r", limit)

    # Optimization: use grep in order to reduce amount of read lines based on
    # some frequently used filters.
    #
    # It's ok if the filters don't match 100% accurately on the right lines. If in
    # doubt, you can output more lines than necessary. This is only a kind of
    # prefiltering.
    greptexts = []
    for filter_name, opfunc, args in filters:
        # Make sure that the greptexts are in the same order as in the
        # actual logfiles. They will be joined with ".*"!
        try:
            nr = grepping_filters.index(filter_name)
            if opfunc in [filter_operators['='], filter_operators['~~']]:
                greptexts.append((nr, str(args)))
        except Exception:
            pass

    greptexts.sort()
    greptexts = [x[1] for x in greptexts]

    status_logger.debug("Texts for grep: %r", greptexts)

    time_filters = [f for f in filters
                    if f[0].split("_")[-1] == "time"]

    status_logger.debug("Time filters: %r", time_filters)

    # We do not want to open all files. So our strategy is:
    # look for "time" filters and first apply the filter to
    # the first entry and modification time of the file. Only
    # if at least one of both timestamps is accepted then we
    # take that file into account.
    # Use the later logfiles first, to get the newer log entries
    # first. When a limit is reached, the newer entries should
    # be processed in most cases. We assume that now.
    # To keep a consistent order of log entries, we should care
    # about sorting the log lines in reverse, but that seems to
    # already be done by the GUI, so we don't do that twice. Skipping
    # this # will lead into some lines of a single file to be limited in
    # wrong order. But this should be better than before.
    for ts, path in sorted(((int(str(path.name)[:-4]), path)
                            for path in settings.paths.history_dir.value.glob('*.log')),
                           reverse=True):
        if limit is not None and limit <= 0:
            break
        first_entry, last_entry = get_logfile_timespan(path)
        for _unused_name, opfunc, argument in time_filters:
            if opfunc(first_entry, argument):
                break
            if opfunc(last_entry, argument):
                break
        else:
            # If no filter matches but we *have* filters
            # then we skip this file. It cannot contain
            # any useful entry for us.
            if len(time_filters):
                if settings.options.debug:
                    logger.info("Skipping logfile %s.log because of time filter" % ts)
                continue  # skip this file

        new_entries = parse_history_file(table_history, path, query, greptexts, limit)
        history_entries += new_entries
        if limit is not None:
            limit -= len(new_entries)

    return history_entries


def parse_history_file(table_history, path, query, greptexts, limit):
    entries = []
    line_no = 0
    # If we have greptexts we pre-filter the file using the extremely
    # fast GNU Grep
    # Revert lines from the log file to have the newer lines processed first
    cmd = 'tac %s' % quote_shell_string(str(path))
    if greptexts:
        cmd += " | egrep -i -e %s" % quote_shell_string(".*".join(greptexts))
    grep = subprocess.Popen(cmd, shell=True, close_fds=True, stdout=subprocess.PIPE)  # nosec

    headers = table_history.column_names

    for line in grep.stdout:
        line_no += 1
        if limit is not None and len(entries) > limit:
            grep.kill()
            grep.wait()
            break

        try:
            parts = line.decode('utf-8').rstrip('\n').split('\t')
            convert_history_line(parts)
            values = [line_no] + parts
            if table_history.filter_row(query, values):
                entries.append(values)
        except Exception as e:
            logger.exception("Invalid line '%s' in history file %s: %s" % (line, path, e))

    return entries


def get_logfile_timespan(path):
    try:
        with path.open(encoding="utf-8") as f:
            first_entry = float(f.readline().split('\t', 1)[0])
    except Exception:
        first_entry = 0.0
    try:
        last_entry = path.stat().st_mtime
    except Exception:
        last_entry = 0.0
    return first_entry, last_entry


#.
#   .--Perfcounters--------------------------------------------------------.
#   |      ____            __                       _                      |
#   |     |  _ \ ___ _ __ / _| ___ ___  _   _ _ __ | |_ ___ _ __ ___       |
#   |     | |_) / _ \ '__| |_ / __/ _ \| | | | '_ \| __/ _ \ '__/ __|      |
#   |     |  __/  __/ |  |  _| (_| (_) | |_| | | | | ||  __/ |  \__ \      |
#   |     |_|   \___|_|  |_|  \___\___/ \__,_|_| |_|\__\___|_|  |___/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Helper class for performance counting                               |
#   '----------------------------------------------------------------------'

def lerp(a, b, t):
    """Linear interpolation between a and b with weight t"""
    return (1 - t) * a + t * b;


class Perfcounters(object):
    _counter_names = [
        "messages",
        "rule_tries",
        "rule_hits",
        "drops",
        "overflows",
        "events",
        "connects",
    ]

    # Average processing times
    _weights = {
        "processing": 0.99,  # event processing
        "sync": 0.95,        # Replication sync
        "request": 0.95,     # Client requests
    }

    # TODO: Why aren't self._times / self._rates / ... not initialized with their defaults?
    def __init__(self):
        self._lock = ECLock("perfcounters")

        # Initialize counters
        self._counters = dict([(n, 0) for n in self._counter_names])

        self._old_counters = {}
        self._rates = {}
        self._average_rates = {}
        self._times = {}
        self._last_statistics = None

        self._logger = logger.getChild("Perfcounters")

    def count(self, counter):
        with self._lock:
            self._counters[counter] += 1

    def count_time(self, counter, ptime):
        with self._lock:
            if counter in self._times:
                self._times[counter] = lerp(ptime, self._times[counter], self._weights[counter])
            else:
                self._times[counter] = ptime

    def do_statistics(self):
        with self._lock:
            now = time.time()
            if self._last_statistics:
                duration = now - self._last_statistics
            else:
                duration = 0
            for name, value in self._counters.iteritems():
                if duration:
                    delta = value - self._old_counters[name]
                    rate = delta / duration
                    self._rates[name] = rate
                    if name in self._average_rates:
                        # We could make the weight configurable
                        self._average_rates[name] = lerp(rate, self._average_rates[name], 0.9)
                    else:
                        self._average_rates[name] = rate

            self._last_statistics = now
            self._old_counters = self._counters.copy()

    @classmethod
    def status_columns(cls):
        columns = []
        # Please note: status_columns() and get_status() need to produce lists with exact same column order
        for name in cls._counter_names:
            columns.append(("status_" + name, 0))
            columns.append(("status_" + name.rstrip("s") + "_rate", 0.0))
            columns.append(("status_average_" + name.rstrip("s") + "_rate", 0.0))

        for name in cls._weights:
            columns.append(("status_average_%s_time" % name, 0.0))

        return columns

    def get_status(self):
        with self._lock:
            row = []
            # Please note: status_columns() and get_status() need to produce lists with exact same column order
            for name in self._counter_names:
                row.append(self._counters[name])
                row.append(self._rates.get(name, 0.0))
                row.append(self._average_rates.get(name, 0.0))

            for name in self._weights:
                row.append(self._times.get(name, 0.0))

            return row


#.
#   .--EventServer---------------------------------------------------------.
#   |      _____                 _   ____                                  |
#   |     | ____|_   _____ _ __ | |_/ ___|  ___ _ ____   _____ _ __        |
#   |     |  _| \ \ / / _ \ '_ \| __\___ \ / _ \ '__\ \ / / _ \ '__|       |
#   |     | |___ \ V /  __/ | | | |_ ___) |  __/ |   \ V /  __/ |          |
#   |     |_____| \_/ \___|_| |_|\__|____/ \___|_|    \_/ \___|_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Verarbeitung und Klassifizierung von eingehenden Events.            |
#   '----------------------------------------------------------------------'

class EventServer(ECServerThread):
    month_names = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                   "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

    def __init__(self, settings, config, slave_status, perfcounters, event_status, table_events):
        super(EventServer, self).__init__(name="EventServer",
                                          settings=settings,
                                          config=config,
                                          slave_status=slave_status,
                                          table_events=table_events,
                                          profiling_enabled=settings.options.profile_event,
                                          profile_file=settings.paths.event_server_profile.value)
        self._syslog = None
        self._syslog_tcp = None
        self._snmptrap = None
        self._mib_resolver = None
        self._snmp_logger = self._logger.getChild("snmp")

        self._rules = []
        self._hash_stats = []
        for _unused_facility in xrange(32):
            self._hash_stats.append([0] * 8)

        self.host_config = HostConfig()
        self._perfcounters = perfcounters
        self._event_status = event_status

        self.create_pipe()
        self.open_eventsocket()
        self.open_syslog()
        self.open_syslog_tcp()
        self.open_snmptrap()

    @classmethod
    def status_columns(cls):
        columns = cls._general_columns()
        columns += Perfcounters.status_columns()
        columns += cls._replication_columns()
        columns += cls._event_limit_columns()
        return columns

    @classmethod
    def _general_columns(cls):
        return [
            ("status_config_load_time", 0),
            ("status_num_open_events", 0),
            ("status_virtual_memory_size", 0),
        ]

    @classmethod
    def _replication_columns(cls):
        return [
            ("status_replication_slavemode", ""),
            ("status_replication_last_sync", 0.0),
            ("status_replication_success", False),
        ]

    @classmethod
    def _event_limit_columns(cls):
        return [
            ("status_event_limit_host", 0),
            ("status_event_limit_rule", 0),
            ("status_event_limit_overall", 0),
            ("status_event_limit_active_hosts", []),
            ("status_event_limit_active_rules", []),
            ("status_event_limit_active_overall", False),
        ]

    def get_status(self):
        row = []

        row += self._add_general_status()
        row += self._perfcounters.get_status()
        row += self._add_replication_status()
        row += self._add_event_limit_status()

        return [row]

    def _add_general_status(self):
        return [
            self._config["last_reload"],
            self._event_status.num_existing_events,
            self._virtual_memory_size(),
        ]

    def _virtual_memory_size(self):
        parts = file('/proc/self/stat').read().split()
        return int(parts[22])  # in Bytes

    def _add_replication_status(self):
        if is_replication_slave(self._config):
            return [
                self._slave_status["mode"],
                self._slave_status["last_sync"],
                self._slave_status["success"],
            ]
        else:
            return ["master", 0.0, False]

    def _add_event_limit_status(self):
        return [
            self._config["event_limit"]["by_host"]["limit"],
            self._config["event_limit"]["by_rule"]["limit"],
            self._config["event_limit"]["overall"]["limit"],
            self.get_hosts_with_active_event_limit(),
            self.get_rules_with_active_event_limit(),
            self.is_overall_event_limit_active(),
        ]

    def create_pipe(self):
        path = self.settings.paths.event_pipe.value
        try:
            if not path.is_fifo():
                path.unlink()
        except Exception:
            pass

        if not path.exists():
            os.mkfifo(str(path))

        # We want to be able to receive events from all users on the local system
        path.chmod(0o666)  # nosec

        self._logger.info("Created FIFO '%s' for receiving events" % path)

    def open_syslog(self):
        endpoint = self.settings.options.syslog_udp
        try:
            if isinstance(endpoint, cmk.ec.settings.FileDescriptor):
                self._syslog = socket.fromfd(endpoint.value, socket.AF_INET, socket.SOCK_DGRAM)
                os.close(endpoint.value)
                self._logger.info("Opened builtin syslog server on inherited filedescriptor %d" % endpoint.value)
            if isinstance(endpoint, cmk.ec.settings.PortNumber):
                self._syslog = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._syslog.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._syslog.bind(("0.0.0.0", endpoint.value))
                self._logger.info("Opened builtin syslog server on UDP port %d" % endpoint.value)
        except Exception as e:
            raise Exception("Cannot start builtin syslog server: %s" % e)

    def open_syslog_tcp(self):
        endpoint = self.settings.options.syslog_tcp
        try:
            if isinstance(endpoint, cmk.ec.settings.FileDescriptor):
                self._syslog_tcp = socket.fromfd(endpoint.value, socket.AF_INET, socket.SOCK_STREAM)
                self._syslog_tcp.listen(20)
                os.close(endpoint.value)
                self._logger.info("Opened builtin syslog-tcp server on inherited filedescriptor %d" % endpoint.value)
            if isinstance(endpoint, cmk.ec.settings.PortNumber):
                self._syslog_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._syslog_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._syslog_tcp.bind(("0.0.0.0", endpoint.value))
                self._syslog_tcp.listen(20)
                self._logger.info("Opened builtin syslog-tcp server on TCP port %d" % endpoint.value)
        except Exception as e:
            raise Exception("Cannot start builtin syslog-tcp server: %s" % e)

    def open_snmptrap(self):
        endpoint = self.settings.options.snmptrap_udp
        try:
            if isinstance(endpoint, cmk.ec.settings.FileDescriptor):
                self._snmptrap = socket.fromfd(endpoint.value, socket.AF_INET, socket.SOCK_DGRAM)
                os.close(endpoint.value)
                self._logger.info("Opened builtin snmptrap server on inherited filedescriptor %d" % endpoint.value)
            if isinstance(endpoint, cmk.ec.settings.PortNumber):
                self._snmptrap = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._snmptrap.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._snmptrap.bind(("0.0.0.0", endpoint.value))
                self._logger.info("Opened builtin snmptrap server on UDP port %d" % endpoint.value)
        except Exception as e:
            raise Exception("Cannot start builtin snmptrap server: %s" % e)

    def open_eventsocket(self):
        path = self.settings.paths.event_socket.value
        if path.exists():
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._eventsocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._eventsocket.bind(str(path))
        path.chmod(0o664)
        self._eventsocket.listen(self._config['eventsocket_queue_len'])
        self._logger.info("Opened UNIX socket '%s' for receiving events" % path)

    def open_pipe(self):
        # Beware: we must open the pipe also for writing. Otherwise
        # we will see EOF forever after one writer has finished and
        # select() will trigger even if there is no data. A good article
        # about this is here:
        # http://www.outflux.net/blog/archives/2008/03/09/using-select-on-a-fifo/
        return os.open(str(self.settings.paths.event_pipe.value), os.O_RDWR | os.O_NONBLOCK)

    def load_mibs(self):
        try:
            builder = MibBuilder()  # manages python MIB modules

            # load MIBs from our compiled MIB and default MIB paths
            builder.setMibSources(*[DirMibSource(str(self.settings.paths.compiled_mibs_dir.value))] + list(builder.getMibSources()))

            # Indicate we wish to load DESCRIPTION and other texts from MIBs
            builder.loadTexts = True

            # This loads all or specified pysnmp MIBs into memory
            builder.loadModules()

            loaded_mib_module_names = builder.mibSymbols.keys()
            self._snmp_logger.info('Loaded %d SNMP MIB modules' % len(loaded_mib_module_names))
            self._snmp_logger.verbose('Found modules: %s' % (', '.join(loaded_mib_module_names)))

            # This object maintains various indices built from MIBs data
            self._mib_resolver = MibViewController(builder)
        except SmiError as e:
            if self.settings.options.debug:
                raise
            self._snmp_logger.info("Exception while loading MIB modules. Proceeding without modules!")
            self._snmp_logger.exception("Exception: %s" % e)

    # Format time difference seconds into approximated
    # human readable value
    def fmt_timeticks(self, ticks):
        secs = float(ticks) / 100
        if secs < 240:
            return "%d sec" % secs
        mins = secs / 60

        if mins < 120:
            return "%d min" % mins

        hours, mins = divmod(mins, 60)
        if hours < 48:
            return "%d hours, %d min" % (hours, mins)

        days, hours = divmod(hours, 24)
        return "%d days, %d hours, %d min" % (days, hours, mins)

    # Convert pysnmp datatypes to simply handable ones
    def snmptrap_convert_var_binds(self, var_bind_list):
        var_binds = []
        for oid, value in var_bind_list:
            key = str(oid)

            if value.__class__.__name__ in ['ObjectIdentifier', 'IpAddress']:
                val = value.prettyPrint()
            elif value.__class__.__name__ == 'TimeTicks':
                val = self.fmt_timeticks(value._value)
            else:
                val = value._value

            # Translate some standard SNMPv2 oids
            if key == '1.3.6.1.2.1.1.3.0':
                key = 'Uptime'

            var_binds.append((key, val))
        return var_binds

    # Convert pysnmp datatypes to simply handable ones
    def snmptrap_translate_varbinds(self, ipaddress, var_bind_list):
        var_binds = []
        if self._mib_resolver is None:
            self._snmp_logger.warning('Failed to translate OIDs, no modules loaded (see above)')
            return [(str(oid), str(value)) for oid, value in var_bind_list]

        def translate(oid, value):
            # Disable mib_var[0] type detection
            # pylint: disable=no-member
            mib_var = ObjectType(ObjectIdentity(oid), value).resolveWithMib(self._mib_resolver)

            node = mib_var[0].getMibNode()
            translated_oid = mib_var[0].prettyPrint().replace("\"", "")
            translated_value = mib_var[1].prettyPrint()

            return node, translated_oid, translated_value

        for oid, value in var_bind_list:
            try:
                node, translated_oid, translated_value = translate(oid, value)

                if hasattr(node, "getUnits"):
                    translated_value += ' ' + node.getUnits()

                if hasattr(node, "getDescription") \
                   and type(self._config["translate_snmptraps"]) == tuple \
                   and "add_description" in self._config["translate_snmptraps"][1]:
                    translated_value += "(%s)" % node.getDescription()

                var_binds.append((translated_oid, translated_value))

            except (SmiError, ValueConstraintError) as e:
                self._snmp_logger.warning('Failed to translate OID %s (in trap from %s): %s '
                                    '(enable debug logging for details)' %
                                    (oid.prettyPrint(), ipaddress, e))
                self._snmp_logger.debug('Failed trap var binds:\n%s' % "\n".join(["%s: %r" % i for i in var_bind_list]))
                self._snmp_logger.debug(traceback.format_exc())

                var_binds.append((str(oid), str(value)))  # add untranslated

        return var_binds

    # Receives an incoming SNMP trap from the socket and hands it over to PySNMP for parsing
    # and processing. PySNMP is calling self.handle_snmptrap back.
    def process_snmptrap(self, data):
        whole_msg, sender_address = data
        self._snmp_logger.verbose("Trap received from %s:%d. Checking for acceptance now." % sender_address)
        g_snmp_engine.setUserContext(sender_address=sender_address)
        g_snmp_engine.msgAndPduDsp.receiveMessage(
            snmpEngine=g_snmp_engine,
            transportDomain=(),
            transportAddress=sender_address,
            wholeMsg=whole_msg
        )

    def handle_snmptrap(self, snmp_engine, state_reference, context_engine_id, context_name,
                        var_binds, cb_ctx):
        ipaddress = snmp_engine.getUserContext("sender_address")[0]

        self.log_snmptrap_details(context_engine_id, context_name, var_binds, ipaddress)

        if snmptrap_translation_enabled(self._config):
            trap = self.snmptrap_translate_varbinds(ipaddress, var_binds)
        else:
            trap = self.snmptrap_convert_var_binds(var_binds)

        event = self.create_event_from_trap(trap, ipaddress)
        self.process_event(event)

    def handle_unauthenticated_snmptrap(self, snmp_engine, execpoint, variables, cb_ctx):
        if variables["securityLevel"] in [ 1, 2 ] and variables["statusInformation"]["errorIndication"] == snmp_errind.unknownCommunityName:
            msg = "Unknown community (%s)" % variables["statusInformation"].get("communityName", "")
        elif variables["securityLevel"] == 3 and variables["statusInformation"]["errorIndication"] == snmp_errind.unknownSecurityName:
            msg = "Unknown credentials (msgUserName: %s)" % variables["statusInformation"].get("msgUserName", "")
        else:
            msg = "%s" % variables["statusInformation"]

        self._snmp_logger.verbose("Trap (v%d) dropped from %s: %s",
            variables["securityLevel"], variables["transportAddress"][0], msg)

    def log_snmptrap_details(self, context_engine_id, context_name, var_binds, ipaddress):
        if self._snmp_logger.is_verbose():
            self._snmp_logger.verbose('Trap accepted from %s (ContextEngineId "%s", ContextName "%s")' %
                                (ipaddress, context_engine_id.prettyPrint(), context_name.prettyPrint()))

            for name, val in var_binds:
                self._snmp_logger.verbose('%-40s = %s' % (name.prettyPrint(), val.prettyPrint()))

    def create_event_from_trap(self, trap, ipaddress):
        # use the trap-oid as application
        application = u''
        for index, (oid, _unused_val) in enumerate(trap):
            if oid in ['1.3.6.1.6.3.1.1.4.1.0', 'SNMPv2-MIB::snmpTrapOID.0']:
                application = scrub_and_decode(trap.pop(index)[1])
                break

        # once we got here we have a real parsed trap which we convert to an event now
        safe_ipaddress = scrub_and_decode(ipaddress)
        text = scrub_and_decode(', '.join(['%s: %s' % (item[0], str(item[1])) for item in trap]))

        event = {
            'time': time.time(),
            'host': safe_ipaddress,
            'ipaddress': safe_ipaddress,
            'priority': 5,  # notice
            'facility': 31,  # not used by syslog -> we use this for all traps
            'application': application,
            'text': text,
            'core_host' : '',
            'host_in_downtime' : False,
        }

        return event

    def serve(self):
        pipe_fragment = ''
        pipe = self.open_pipe()
        listen_list = [pipe]

        # Wait for incoming syslog packets via UDP
        if self._syslog is not None:
            listen_list.append(self._syslog.fileno())

        # Wait for new connections for events via TCP socket
        if self._syslog_tcp is not None:
            listen_list.append(self._syslog_tcp)

        # Wait for new connections for events via unix socket
        if self._eventsocket:
            listen_list.append(self._eventsocket)

        # Wait for incomding SNMP traps
        if self._snmptrap is not None:
            listen_list.append(self._snmptrap.fileno())

        # Keep list of client connections via UNIX socket and
        # read data that is not yet processed. Map from
        # fd to (fileobject, data)
        client_sockets = {}
        select_timeout = 1
        while not self._shal_terminate():
            try:
                readable = select.select(listen_list + client_sockets.keys(), [], [], select_timeout)[0]
            except select.error as e:
                if e[0] == errno.EINTR:
                    continue
                raise
            data = None

            # Accept new connection on event unix socket
            if self._eventsocket in readable:
                client_socket, address = self._eventsocket.accept()
                # pylint: disable=no-member
                client_sockets[client_socket.fileno()] = (client_socket, address, "")

            # Same for the TCP syslog socket
            if self._syslog_tcp and self._syslog_tcp in readable:
                client_socket, address = self._syslog_tcp.accept()
                # pylint: disable=no-member
                client_sockets[client_socket.fileno()] = (client_socket, address, "")

            # Read data from existing event unix socket connections
            # NOTE: We modify client_socket in the loop, so we need to copy below!
            for fd, (cs, address, previous_data) in list(client_sockets.iteritems()):
                if fd in readable:
                    # Receive next part of data
                    try:
                        new_data = cs.recv(4096)
                    except Exception:
                        new_data = ""
                        address = None

                    # Put together with incomplete messages from last time
                    data = previous_data + new_data

                    # Do we have incomplete data? (if the socket has been
                    # closed then we consider the pending message always
                    # as complete, even if there was no trailing \n)
                    if new_data and not data.endswith("\n"):  # keep fragment
                        # Do we have any complete messages?
                        if '\n' in data:
                            complete, rest = data.rsplit("\n", 1)
                            self.process_raw_lines(complete + "\n", address)
                        else:
                            rest = data  # keep for next time

                    # Only complete messages
                    else:
                        if data:
                            self.process_raw_lines(data, address)
                        rest = ""

                    # Connection still open?
                    if new_data:
                        client_sockets[fd] = (cs, address, rest)
                    else:
                        cs.close()
                        del client_sockets[fd]

            # Read data from pipe
            if pipe in readable:
                try:
                    data = os.read(pipe, 4096)
                    if len(data) == 0:  # END OF FILE!
                        os.close(pipe)
                        pipe = self.open_pipe()
                        listen_list[0] = pipe
                        # Pending fragments from previos reads that are not terminated
                        # by a \n are ignored.
                        if pipe_fragment:
                            self._logger.warning("Ignoring incomplete message '%s' from pipe" % pipe_fragment)
                            pipe_fragment = ""
                    else:
                        # Prepend previous beginning of message to read data
                        data = pipe_fragment + data
                        pipe_fragment = ""

                        # Last message still incomplete?
                        if data[-1] != '\n':
                            if '\n' in data:  # at least one complete message contained
                                messages, pipe_fragment = data.rsplit('\n', 1)
                                self.process_raw_lines(messages + '\n')  # got lost in split
                            else:
                                pipe_fragment = data  # keep beginning of message, wait for \n
                        else:
                            self.process_raw_lines(data)
                except Exception:
                    pass

            # Read events from builtin syslog server
            if self._syslog is not None and self._syslog.fileno() in readable:
                self.process_raw_lines(*self._syslog.recvfrom(4096))

            # Read events from builtin snmptrap server
            if self._snmptrap is not None and self._snmptrap.fileno() in readable:
                try:
                    data = self._snmptrap.recvfrom(65535)
                    self.process_raw_data(self.process_snmptrap, data)
                except Exception:
                    self._logger.exception('Exception handling a SNMP trap from "%s". Skipping this one' %
                                          (data[1][0]))

            try:
                # process the first spool file we get
                spool_file = next(self.settings.paths.spool_dir.value.glob('[!.]*'))
                self.process_raw_lines(spool_file.read_bytes())
                spool_file.unlink()
                select_timeout = 0  # enable fast processing to process further files
            except StopIteration:
                select_timeout = 1  # restore default select timeout

    # Processes incoming data, just a wrapper between the real data and the
    # handler function to record some statistics etc.
    def process_raw_data(self, handler_func, data):
        self._perfcounters.count("messages")
        before = time.time()
        # In replication slave mode (when not took over), ignore all events
        if not is_replication_slave(self._config) or self._slave_status["mode"] != "sync":
            handler_func(data)
        elif self.settings.options.debug:
            self._logger.info("Replication: we are in slave mode, ignoring event")
        elapsed = time.time() - before
        self._perfcounters.count_time("processing", elapsed)

    # Takes several lines of messages, handles encoding and processes them separated
    def process_raw_lines(self, data, address=None):
        lines = data.splitlines()
        for line in lines:
            line = scrub_and_decode(line.rstrip())
            if line:
                try:
                    self.process_raw_data(self.process_line, (line, address))
                except Exception as e:
                    self._logger.exception('Exception handling a log line (skipping this one): %s' % e)

    def do_housekeeping(self):
        with lock_eventstatus:
            with lock_configuration:
                self.hk_handle_event_timeouts()
                self.hk_check_expected_messages()
                self.hk_cleanup_downtime_events()

        if self._config['archive_mode'] != 'mongodb':
            with lock_logging:
                expire_logfiles(self.settings, self._config)

    # For all events that have been created in a host downtime check the host
    # whether or not it is still in downtime. In case the downtime has ended
    # archive the events that have been created in a downtime.
    def hk_cleanup_downtime_events(self):
        host_downtimes = {}

        for event in self._event_status.events():
            if not event["host_in_downtime"]:
                continue  # only care about events created in downtime

            try:
                in_downtime = host_downtimes[event["core_host"]]
            except KeyError:
                in_downtime = self._is_host_in_downtime(event)
                host_downtimes[event["core_host"]] = in_downtime

            if in_downtime:
                continue  # (still) in downtime, don't delete any event

            self._logger.verbose("Remove event %d (created in downtime, host left downtime)" % event["id"])
            self._event_status.remove_event(event)

    def hk_handle_event_timeouts(self):
        # 1. Automatically delete all events that are in state "counting"
        #    and have not reached the required number of hits and whose
        #    time is elapsed.
        # 2. Automatically delete all events that are in state "open"
        #    and whose livetime is elapsed.
        events_to_delete = []
        events = self._event_status.events()
        now = time.time()
        for nr, event in enumerate(events):
            rule = self._rule_by_id.get(event["rule_id"])

            if event["phase"] == "counting":
                # Event belongs to a rule that does not longer exist? It
                # will never reach its count. Better delete it.
                if not rule:
                    self._logger.info("Deleting orphaned event %d created by obsolete rule %s" %
                                     (event["id"], event["rule_id"]))
                    event["phase"] = "closed"
                    log_event_history(self.settings, self._config, self._table_events, event, "ORPHANED")
                    events_to_delete.append(nr)

                elif "count" not in rule and "expect" not in rule:
                    self._logger.info("Count-based event %d belonging to rule %s: rule does not "
                                     "count/expect anymore. Deleting event." % (event["id"], event["rule_id"]))
                    event["phase"] = "closed"
                    log_event_history(self.settings, self._config, self._table_events, event, "NOCOUNT")
                    events_to_delete.append(nr)

                # handle counting
                elif "count" in rule:
                    count = rule["count"]
                    if count.get("algorithm") in ["tokenbucket", "dynabucket"]:
                        last_token = event.get("last_token", event["first"])
                        secs_per_token = count["period"] / float(count["count"])
                        if count["algorithm"] == "dynabucket":  # get fewer tokens if count is lower
                            if event["count"] <= 1:
                                secs_per_token = count["period"]
                            else:
                                secs_per_token *= (float(count["count"]) / float(event["count"]))
                        elapsed_secs = now - last_token
                        new_tokens = int(elapsed_secs / secs_per_token)
                        if new_tokens:
                            if self.settings.options.debug:
                                self._logger.info("Rule %s/%s, event %d: got %d new tokens" %
                                                 (rule["pack"], rule["id"], event["id"], new_tokens))
                            event["count"] = max(0, event["count"] - new_tokens)
                            event["last_token"] = last_token + new_tokens * secs_per_token  # not now! would be unfair
                            if event["count"] == 0:
                                self._logger.info("Rule %s/%s, event %d: again without allowed rate, dropping event" %
                                                 (rule["pack"], rule["id"], event["id"]))
                                event["phase"] = "closed"
                                log_event_history(self.settings, self._config, self._table_events, event, "COUNTFAILED")
                                events_to_delete.append(nr)

                    else:  # algorithm 'interval'
                        if event["first"] + count["period"] <= now:  # End of period reached
                            self._logger.info("Rule %s/%s: reached only %d out of %d events within %d seconds. "
                                             "Resetting to zero." % (rule["pack"], rule["id"], event["count"],
                                                                     count["count"], count["period"]))
                            event["phase"] = "closed"
                            log_event_history(self.settings, self._config, self._table_events, event, "COUNTFAILED")
                            events_to_delete.append(nr)

            # Handle delayed actions
            elif event["phase"] == "delayed":
                delay_until = event.get("delay_until", 0)  # should always be present
                if now >= delay_until:
                    self._logger.info("Delayed event %d of rule %s is now activated." % (event["id"], event["rule_id"]))
                    event["phase"] = "open"
                    log_event_history(self.settings, self._config, self._table_events, event, "DELAYOVER")
                    if rule:
                        event_has_opened(self.settings, self._config, self, self._table_events, rule, event)
                        if rule.get("autodelete"):
                            event["phase"] = "closed"
                            log_event_history(self.settings, self._config, self._table_events, event, "AUTODELETE")
                            events_to_delete.append(nr)

                    else:
                        self._logger.info("Cannot do rule action: rule %s not present anymore." % event["rule_id"])

            # Handle events with a limited lifetime
            elif "live_until" in event:
                if now >= event["live_until"]:
                    allowed_phases = event.get("live_until_phases", ["open"])
                    if event["phase"] in allowed_phases:
                        event["phase"] = "closed"
                        events_to_delete.append(nr)
                        self._logger.info("Livetime of event %d (rule %s) exceeded. Deleting event." %
                                         (event["id"], event["rule_id"]))
                        log_event_history(self.settings, self._config, self._table_events, event, "EXPIRED")

        # Do delayed deletion now (was delayed in order to keep list indices OK)
        for nr in events_to_delete[::-1]:
            self._event_status.remove_event(events[nr])

    def hk_check_expected_messages(self):
        now = time.time()
        # "Expecting"-rules are rules that require one or several
        # occurrances of a message within a defined time period.
        # Whenever one period of time has elapsed, we need to check
        # how many messages have been seen for that rule. If these
        # are too few, we open an event.
        # We need to handle to cases:
        # 1. An event for such a rule already exists and is
        #    in the state "counting" -> this can only be the case if
        #    more than one occurrance is required.
        # 2. No event at all exists.
        #    in that case.
        for rule in self._rules:
            if "expect" in rule:

                if not self.event_rule_matches_site(rule, event=None):
                    continue

                # Interval is either a number of seconds, or pair of a number of seconds
                # (e.g. 86400, meaning one day) and a timezone offset relative to UTC in hours.
                interval = rule["expect"]["interval"]
                expected_count = rule["expect"]["count"]

                interval_start = self._event_status.interval_start(rule["id"], interval)
                if interval_start >= now:
                    continue

                next_interval_start = self._event_status.next_interval_start(interval, interval_start)
                if next_interval_start > now:
                    continue

                # Interval has been elapsed. Now comes the truth: do we have enough
                # rule matches?

                # First do not forget to switch to next interval
                self._event_status.start_next_interval(rule["id"], interval)

                # First look for case 1: rule that already have at least one hit
                # and this events in the state "counting" exist.
                events_to_delete = []
                events = self._event_status.events()
                for nr, event in enumerate(events):
                    if event["rule_id"] == rule["id"] and event["phase"] == "counting":
                        # time has elapsed. Now lets see if we have reached
                        # the neccessary count:
                        if event["count"] < expected_count:  # no -> trigger alarm
                            self._handle_absent_event(rule, event["count"], expected_count, event["last"])
                        else:  # yes -> everything is fine. Just log.
                            self._logger.info("Rule %s/%s has reached %d occurrances (%d required). "
                                             "Starting next period." %
                                             (rule["pack"], rule["id"], event["count"], expected_count))
                            log_event_history(self.settings, self._config, self._table_events, event, "COUNTREACHED")
                        # Counting event is no longer needed.
                        events_to_delete.append(nr)
                        break

                # Ou ou, no event found at all.
                else:
                    self._handle_absent_event(rule, 0, expected_count, interval_start)

                for nr in events_to_delete[::-1]:
                    self._event_status.remove_event(events[nr])

    def _handle_absent_event(self, rule, event_count, expected_count, interval_start):
        now = time.time()
        if event_count:
            text = "Expected message arrived only %d out of %d times since %s" % \
                   (event_count, expected_count, time.strftime("%F %T", time.localtime(interval_start)))
        else:
            text = "Expected message did not arrive since %s" % \
                   time.strftime("%F %T", time.localtime(interval_start))

        # If there is already an incidence about this absent message, we can merge and
        # not create a new event. There is a setting for this.
        merge_event = None
        merge = rule["expect"].get("merge", "open")
        if merge != "never":
            for event in self._event_status.events():
                if event["rule_id"] == rule["id"] and \
                        (event["phase"] == "open" or
                         (event["phase"] == "ack" and merge == "acked")):
                    merge_event = event
                    break

        if merge_event:
            merge_event["last"] = now
            merge_event["count"] += 1
            merge_event["phase"] = "open"
            merge_event["time"] = now
            merge_event["text"] = text
            # Better rewrite (again). Rule might have changed. Also we have changed
            # the text and the user might have his own text added via set_text.
            self.rewrite_event(rule, merge_event, {}, set_first=False)
            log_event_history(self.settings, self._config, self._table_events, merge_event, "COUNTFAILED")
        else:
            # Create artifical event from scratch. Make sure that all important
            # fields are defined.
            event = {
                "rule_id": rule["id"],
                "text": text,
                "phase": "open",
                "count": 1,
                "time": now,
                "first": now,
                "last": now,
                "comment": "",
                "host": "",
                "ipaddress": "",
                "application": "",
                "pid": 0,
                "priority": 3,
                "facility": 1,  # user
                "match_groups": (),
                "match_groups_syslog_application": (),
                "core_host": "",
                "host_in_downtime": False,
            }
            self._add_rule_contact_groups_to_event(rule, event)
            self.rewrite_event(rule, event, {})
            self._event_status.new_event(self._table_events, event)
            log_event_history(self.settings, self._config, self._table_events, event, "COUNTFAILED")
            event_has_opened(self.settings, self._config, self, self._table_events, rule, event)
            if rule.get("autodelete"):
                event["phase"] = "closed"
                log_event_history(self.settings, self._config, self._table_events, event, "AUTODELETE")
                self._event_status.remove_event(event)

    def reload_configuration(self, config):
        self._config = config
        self.compile_rules(self._config["rules"], self._config["rule_packs"])
        self.host_config.initialize()

    # Precompile regular expressions and similar stuff. Also convert legacy
    # "rules" parameter into new "rule_packs" parameter
    def compile_rules(self, legacy_rules, rule_packs):
        self._rules = []
        self._rule_by_id = {}
        self._rule_hash = {}  # Speedup-Hash for rule execution
        count_disabled = 0
        count_rules = 0
        count_unspecific = 0

        def compile_matching_value(key, val):
            value = val.strip()
            # Remove leading .* from regex. This is redundant and
            # dramatically destroys performance when doing an infix search.
            if key in ["match", "match_ok"]:
                while value.startswith(".*") and not value.startswith(".*?"):
                    value = value[2:]

            if not value:
                return None

            if cmk.regex.is_regex(value):
                return re.compile(value, re.IGNORECASE)
            else:
                return val.lower()

        # Loop through all rule packages and with through their rules
        for rule_pack in rule_packs:
            if rule_pack["disabled"]:
                count_disabled += len(rule_pack["rules"])
                continue

            for rule in rule_pack["rules"]:
                if rule.get("disabled"):
                    count_disabled += 1
                else:
                    count_rules += 1
                    rule = rule.copy()  # keep original intact because of slave replication

                    # Store information about rule pack right within the rule. This is needed
                    # for debug output and also for skipping rule packs
                    rule["pack"] = rule_pack["id"]
                    self._rules.append(rule)
                    self._rule_by_id[rule["id"]] = rule
                    try:
                        for key in ["match", "match_ok", "match_host", "match_application",
                                    "cancel_application"]:
                            if key in rule:
                                value = compile_matching_value(key, rule[key])
                                if value is None:
                                    del rule[key]
                                    continue

                                rule[key] = value

                        if 'state' in rule and type(rule['state']) == tuple \
                           and rule['state'][0] == 'text_pattern':
                            for key in ['2', '1', '0']:
                                if key in rule['state'][1]:
                                    value = compile_matching_value('state', rule['state'][1][key])
                                    if value is None:
                                        del rule['state'][1][key]
                                    else:
                                        rule['state'][1][key] = value

                    except Exception as e:
                        if self.settings.options.debug:
                            raise
                        rule["disabled"] = True
                        count_disabled += 1
                        self._logger.exception("Ignoring rule '%s/%s' because of an invalid regex (%s)." %
                                              (rule["pack"], rule["id"], e))

                    if self._config["rule_optimizer"]:
                        self.hash_rule(rule)
                        if "match_facility" not in rule \
                                and "match_priority" not in rule \
                                and "cancel_priority" not in rule \
                                and "cancel_application" not in rule:
                            count_unspecific += 1

        self._logger.info("Compiled %d active rules (ignoring %d disabled rules)" % (count_rules, count_disabled))
        if self._config["rule_optimizer"]:
            self._logger.info("Rule hash: %d rules - %d hashed, %d unspecific" %
                             (len(self._rules), len(self._rules) - count_unspecific, count_unspecific))
            for facility in xrange(32):
                if facility in self._rule_hash:
                    stats = []
                    for prio, entries in self._rule_hash[facility].iteritems():
                        stats.append("%s(%d)" % (syslog_priorities[prio], len(entries)))
                    if syslog_facilities[facility]:
                        self._logger.info(" %-12s: %s" % (syslog_facilities[facility], " ".join(stats)))

    def hash_rule(self, rule):
        # Construct rule hash for faster execution.
        facility = rule.get("match_facility")
        if facility and not rule.get("invert_matching"):
            self.hash_rule_facility(rule, facility)
        else:
            for facility in xrange(32):  # all syslog facilities
                self.hash_rule_facility(rule, facility)

    def hash_rule_facility(self, rule, facility):
        needed_prios = [False] * 8
        for key in ["match_priority", "cancel_priority"]:
            if key in rule:
                prio_from, prio_to = rule[key]
                # Beware: from > to!
                for p in xrange(prio_to, prio_from + 1):
                    needed_prios[p] = True
            elif key == "match_priority":  # all priorities match
                needed_prios = [True] * 8  # needed to check this rule for all event priorities
            elif "match_ok" in rule:  # a cancelling rule where all priorities cancel
                needed_prios = [True] * 8  # needed to check this rule for all event priorities

        if rule.get("invert_matching"):
            needed_prios = [True] * 8

        prio_hash = self._rule_hash.setdefault(facility, {})
        for prio, need in enumerate(needed_prios):
            if need:
                prio_hash.setdefault(prio, []).append(rule)

    def output_hash_stats(self):
        self._logger.info("Top 20 of facility/priority:")
        entries = []
        total_count = 0
        for facility in xrange(32):
            for priority in xrange(8):
                count = self._hash_stats[facility][priority]
                if count:
                    total_count += count
                    entries.append((count, (facility, priority)))
        entries.sort()
        entries.reverse()
        for count, (facility, priority) in entries[:20]:
            self._logger.info("  %s/%s - %d (%.2f%%)" % (
                syslog_facilities[facility], syslog_priorities[priority], count,
                (100.0 * count / float(total_count))
            ))

    def process_line(self, data):
        line, address = data
        line = line.rstrip()
        if self._config["debug_rules"]:
            if address:
                self._logger.info(u"Processing message from %r: '%s'" % (address, line))
            else:
                self._logger.info(u"Processing message '%s'" % line)

        event = self.create_event_from_line(line, address)
        self.process_event(event)

    def process_event(self, event):
        self.do_translate_hostname(event)

        # Log all incoming messages into a syslog-like text file if that is enabled
        if self._config["log_messages"]:
            self.log_message(event)

        # Rule optimizer
        if self._config["rule_optimizer"]:
            self._hash_stats[event["facility"]][event["priority"]] += 1
            rule_candidates = self._rule_hash.get(event["facility"], {}).get(event["priority"], [])
        else:
            rule_candidates = self._rules

        skip_pack = None
        for rule in rule_candidates:
            if skip_pack and rule["pack"] == skip_pack:
                continue  # still in the rule pack that we want to skip
            skip_pack = None  # new pack, reset skipping

            try:
                result = self.event_rule_matches(rule, event)
            except Exception as e:
                self._logger.exception('  Exception during matching:\n%s' % e)
                result = False

            if result:  # A tuple with (True/False, {match_info}).. O.o
                self._perfcounters.count("rule_hits")
                cancelling, match_groups = result

                if self._config["debug_rules"]:
                    self._logger.info("  matching groups:\n%s" % pprint.pformat(match_groups))

                self._event_status.count_rule_match(rule["id"])
                if self._config["log_rulehits"]:
                    self._logger.info("Rule '%s/%s' hit by message %s/%s - '%s'." % (
                        rule["pack"], rule["id"],
                        syslog_facilities[event["facility"]], syslog_priorities[event["priority"]],
                        event["text"]))

                if rule.get("drop"):
                    if rule["drop"] == "skip_pack":
                        skip_pack = rule["pack"]
                        if self._config["debug_rules"]:
                            self._logger.info("  skipping this rule pack (%s)" % skip_pack)
                        continue
                    else:
                        self._perfcounters.count("drops")
                        return

                if cancelling:
                    self._event_status.cancel_events(self, self._table_events, event, match_groups, rule)
                    return
                else:
                    # Remember the rule id that this event originated from
                    event["rule_id"] = rule["id"]

                    # Lookup the monitoring core hosts and add the core host
                    # name to the event when one can be matched
                    # For the moment we have no rule/condition matching on this
                    # field. So we only add the core host info for matched events.
                    self._add_core_host_to_new_event(event)

                    # Attach optional contact group information for visibility
                    # and eventually for notifications
                    self._add_rule_contact_groups_to_event(rule, event)

                    # Store groups from matching this event. In order to make
                    # persistence easier, we do not safe them as list but join
                    # them on ASCII-1.
                    event["match_groups"] = match_groups.get("match_groups_message", ())
                    event["match_groups_syslog_application"] = match_groups.get("match_groups_syslog_application", ())
                    self.rewrite_event(rule, event, match_groups)

                    if "count" in rule:
                        count = rule["count"]
                        # Check if a matching event already exists that we need to
                        # count up. If the count reaches the limit, the event will
                        # be opened and its rule actions performed.
                        existing_event = \
                            self._event_status.count_event(self, self._table_events, event, rule, count)
                        if existing_event:
                            if "delay" in rule:
                                if self._config["debug_rules"]:
                                    self._logger.info("Event opening will be delayed for %d seconds" % rule["delay"])
                                existing_event["delay_until"] = time.time() + rule["delay"]
                                existing_event["phase"] = "delayed"
                            else:
                                event_has_opened(self.settings, self._config, self, self._table_events, rule, existing_event)

                            log_event_history(self.settings, self._config, self._table_events, existing_event, "COUNTREACHED")

                            if "delay" not in rule and rule.get("autodelete"):
                                existing_event["phase"] = "closed"
                                log_event_history(self.settings, self._config, self._table_events, existing_event, "AUTODELETE")
                                with lock_eventstatus:
                                    self._event_status.remove_event(existing_event)
                    elif "expect" in rule:
                        self._event_status.count_expected_event(self, self._table_events, event)
                    else:
                        if "delay" in rule:
                            if self._config["debug_rules"]:
                                self._logger.info("Event opening will be delayed for %d seconds" % rule["delay"])
                            event["delay_until"] = time.time() + rule["delay"]
                            event["phase"] = "delayed"
                        else:
                            event["phase"] = "open"

                        if self.new_event_respecting_limits(event):
                            if event["phase"] == "open":
                                event_has_opened(self.settings, self._config, self, self._table_events, rule, event)
                                if rule.get("autodelete"):
                                    event["phase"] = "closed"
                                    log_event_history(self.settings, self._config, self._table_events, event, "AUTODELETE")
                                    with lock_eventstatus:
                                        self._event_status.remove_event(event)
                    return

        # End of loop over rules.
        if self._config["archive_orphans"]:
            self._event_status.archive_event(self._table_events, event)

    def _add_rule_contact_groups_to_event(self, rule, event):
        if rule.get("contact_groups") is None:
            event.update({
                "contact_groups": None,
                "contact_groups_notify": False,
                "contact_groups_precedence": "host",
            })
        else:
            event.update({
                "contact_groups": rule["contact_groups"]["groups"],
                "contact_groups_notify": rule["contact_groups"]["notify"],
                "contact_groups_precedence": rule["contact_groups"]["precedence"],
            })

    def add_core_host_to_event(self, event):
        matched_host = self.host_config.get_by_event_host_name(event["host"])
        if not matched_host:
            event["core_host"] = ""
            return

        event["core_host"] = matched_host["name"]

    def _add_core_host_to_new_event(self, event):
        self.add_core_host_to_event(event)

        # Add some state dependent information (like host is in downtime etc.)
        event["host_in_downtime"] = self._is_host_in_downtime(event)

    def _is_host_in_downtime(self, event):
        if not event["core_host"]:
            return False  # Found no host in core: Not in downtime!

        query = (
            "GET hosts\n"
            "Columns: scheduled_downtime_depth\n"
            "Filter: host_name = %s\n" % (event["core_host"])
        )

        try:
            return livestatus.LocalConnection().query_value(query) >= 1

        except livestatus.MKLivestatusNotFoundError:
            return False

        except Exception:
            if cmk.debug.enabled():
                raise
            return False

    # Checks if an event matches a rule. Returns either False (no match)
    # or a pair of matchtype, groups, where matchtype is False for a
    # normal match and True for a cancelling match and the groups is a tuple
    # if matched regex groups in either text (normal) or match_ok (cancelling)
    # match.
    def event_rule_matches(self, rule, event):
        self._perfcounters.count("rule_tries")
        with lock_configuration:
            result = self.event_rule_matches_non_inverted(rule, event)
            if rule.get("invert_matching"):
                if result is False:
                    result = False, {}
                    if self._config["debug_rules"]:
                        self._logger.info("  Rule would not match, but due to inverted matching does.")
                else:
                    result = False
                    if self._config["debug_rules"]:
                        self._logger.info("  Rule would match, but due to inverted matching does not.")

            return result

    def event_rule_matches_generic(self, rule, event):
        generic_match_functions = [
            self.event_rule_matches_site,
            self.event_rule_matches_host,
            self.event_rule_matches_ip,
            self.event_rule_matches_facility,
            self.event_rule_matches_service_level,
            self.event_rule_matches_timeperiod,
        ]

        for match_function in generic_match_functions:
            if not match_function(rule, event):
                return False
        return True

    def event_rule_matches_site(self, rule, event):
        return "match_site" not in rule or cmk.omd_site() in rule["match_site"]

    def event_rule_matches_host(self, rule, event):
        if match(rule.get("match_host"), event["host"], complete=True) is False:
            if self._config["debug_rules"]:
                self._logger.info("  did not match because of wrong host '%s' (need '%s')" %
                                 (event["host"], pattern(rule.get("match_host"))))
            return False
        return True

    def event_rule_matches_ip(self, rule, event):
        if match_ipv4_network(rule.get("match_ipaddress", "0.0.0.0/0"), event["ipaddress"]) is False:
            if self._config["debug_rules"]:
                self._logger.info("  did not match because of wrong source IP address '%s' (need '%s')" %
                                 (event["ipaddress"], rule.get("match_ipaddress")))
            return False
        return True

    def event_rule_matches_facility(self, rule, event):
        if "match_facility" in rule and event["facility"] != rule["match_facility"]:
            if self._config["debug_rules"]:
                self._logger.info("  did not match because of wrong syslog facility")
            return False
        return True

    def event_rule_matches_service_level(self, rule, event):
        if "match_sl" in rule:
            sl_from, sl_to = rule["match_sl"]
            if sl_from > sl_to:
                sl_to, sl_from = sl_from, sl_to
            p = event.get("sl", 0)
            if p < sl_from or p > sl_to:
                if self._config["debug_rules"]:
                    self._logger.info("  did not match because of wrong service level %d (need %d..%d)" %
                                     (p, sl_from, sl_to),)
                return False
        return True

    def event_rule_matches_timeperiod(self, rule, event):
        if "match_timeperiod" in rule and not check_timeperiod(self.settings, rule["match_timeperiod"]):
            if self._config["debug_rules"]:
                self._logger.info("  did not match, because timeperiod %s is not active" % rule["match_timeperiod"])
            return False
        return True

    def event_rule_determine_match_groups(self, rule, event, match_groups):
        match_group_functions = [
            self.event_rule_matches_syslog_application,
            self.event_rule_matches_message,
        ]
        for match_function in match_group_functions:
            if not match_function(rule, event, match_groups):
                return False
        return True

    def event_rule_matches_syslog_application(self, rule, event, match_groups):
        if "match_application" not in rule and "cancel_application" not in rule:
            return True

        # Syslog application
        if "match_application" in rule:
            match_groups["match_groups_syslog_application"] = match(rule.get("match_application"), event["application"],
                                                                    complete=False)

        # Syslog application canceling, this option must be explictly set
        if "cancel_application" in rule:
            match_groups["match_groups_syslog_application_ok"] = match(rule.get("cancel_application"),
                                                                       event["application"],
                                                                       complete=False)

        # Detect impossible match
        if match_groups.get("match_groups_syslog_application", False) is False and\
           match_groups.get("match_groups_syslog_application_ok", False) is False:
            if self._config["debug_rules"]:
                self._logger.info("  did not match, syslog application does not match")
            return False

        return True

    def event_rule_matches_message(self, rule, event, match_groups):
        # Message matching, this condition is always active
        match_groups["match_groups_message"] = match(rule.get("match"), event["text"], complete=False)

        # Message canceling, this option must be explictly set
        if "match_ok" in rule:
            match_groups["match_groups_message_ok"] = match(rule.get("match_ok"),
                                                            event["text"],
                                                            complete=False)

        # Detect impossible match
        if match_groups["match_groups_message"] is False and\
           match_groups.get("match_groups_message_ok", False) is False:
            if self._config["debug_rules"]:
                self._logger.info("  did not match, message text does not match")
            return False

        return True

    def event_rule_determine_match_priority(self, rule, event, match_priority):
        p = event["priority"]

        if "match_priority" in rule:
            prio_from, prio_to = sorted(rule["match_priority"])
            match_priority["has_match"] = prio_from <= p <= prio_to
        else:
            match_priority["has_match"] = True

        if "cancel_priority" in rule:
            cancel_from, cancel_to = sorted(rule["cancel_priority"])
            match_priority["has_canceling_match"] = cancel_from <= p <= cancel_to
        else:
            match_priority["has_canceling_match"] = False

        if match_priority["has_match"] is False and\
           match_priority["has_canceling_match"] is False:
            return False

        return True

    def event_rule_matches_non_inverted(self, rule, event):
        if self._config["debug_rules"]:
            self._logger.info("Trying rule %s/%s..." % (rule["pack"], rule["id"]))
            self._logger.info("  Text:   %s" % event["text"])
            self._logger.info("  Syslog: %d.%d" % (event["facility"], event["priority"]))
            self._logger.info("  Host:   %s" % event["host"])

        # Generic conditions without positive/canceling matches
        if not self.event_rule_matches_generic(rule, event):
            return False

        # Determine syslog priority
        match_priority = {}
        if not self.event_rule_determine_match_priority(rule, event, match_priority):
            # Abort on negative outcome, neither positive nor negative
            return False

        # Determine and cleanup match_groups
        match_groups = {}
        if not self.event_rule_determine_match_groups(rule, event, match_groups):
            # Abort on negative outcome, neither positive nor negative
            return False
        for group_name in match_groups.keys():
            if match_groups[group_name] is True:
                match_groups[group_name] = ()

        # All data has been computed, determine outcome
        ########################################################
        # Check canceling-event
        has_canceling_condition = bool([x for x in ["match_ok", "cancel_application", "cancel_priority"] if x in rule])
        if has_canceling_condition:
            if ("match_ok" not in rule or match_groups.get("match_groups_message_ok", False) is not False) and\
               ("cancel_application" not in rule or
                match_groups.get("match_groups_syslog_application_ok", False) is not False) and\
               ("cancel_priority" not in rule or match_priority["has_canceling_match"] is True):
                if self._config["debug_rules"]:
                    self._logger.info("  found canceling event")
                return True, match_groups

        # Check create-event
        if match_groups["match_groups_message"] is not False and\
           match_groups.get("match_groups_syslog_application", ()) is not False and\
           match_priority["has_match"] is True:
            if self._config["debug_rules"]:
                self._logger.info("  found new event")
            return False, match_groups

        # Looks like there was no match, output some additonal info
        # Reasons preventing create-event
        if self._config["debug_rules"]:
            if match_groups["match_groups_message"] is False:
                self._logger.info("  did not create event, because of wrong message")
            if "match_application" in rule and match_groups["match_groups_syslog_application"] is False:
                self._logger.info("  did not create event, because of wrong syslog application")
            if "match_priority" in rule and match_priority["has_match"] is False:
                self._logger.info("  did not create event, because of wrong syslog priority")

            if has_canceling_condition:
                # Reasons preventing cancel-event
                if "match_ok" in rule and match_groups.get("match_groups_message_ok", False) is False:
                    self._logger.info("  did not cancel event, because of wrong message")
                if "cancel_application" in rule and \
                   match_groups.get("match_groups_syslog_application_ok", False) is False:
                    self._logger.info("  did not cancel event, because of wrong syslog application")
                if "cancel_priority" in rule and match_priority["has_canceling_match"] is False:
                    self._logger.info("  did not cancel event, because of wrong cancel priority")

        return False

    # Rewrite texts and compute other fields in the event
    def rewrite_event(self, rule, event, groups, set_first=True):
        if rule["state"] == -1:
            prio = event["priority"]
            if prio >= 5:
                event["state"] = 0
            elif prio < 4:
                event["state"] = 2
            else:
                event["state"] = 1
        elif type(rule["state"]) == tuple and rule["state"][0] == "text_pattern":
            for key in ['2', '1', '0', '3']:
                if key in rule["state"][1]:
                    match_groups = match(rule["state"][1][key], event["text"], complete=False)
                    if match_groups is not False:
                        event["state"] = int(key)
                        break
                elif key == '3':  # No rule matched!
                    event["state"] = 3
        else:
            event["state"] = rule["state"]

        if  ("sl" not in event) or (rule["sl"]["precedence"] == "rule"):
            event["sl"] = rule["sl"]["value"]
        if set_first:
            event["first"] = event["time"]
        event["last"] = event["time"]
        if "set_comment" in rule:
            event["comment"] = replace_groups(rule["set_comment"], event["text"], groups)
        if "set_text" in rule:
            event["text"] = replace_groups(rule["set_text"], event["text"], groups)
        if "set_host" in rule:
            event["orig_host"] = event["host"]
            event["host"] = replace_groups(rule["set_host"], event["host"], groups)
        if "set_application" in rule:
            event["application"] = replace_groups(rule["set_application"], event["application"], groups)
        if "set_contact" in rule and "contact" not in event:
            event["contact"] = replace_groups(rule["set_contact"], event.get("contact", ""), groups)

    def parse_syslog_info(self, line):
        event = {}
        # Replaced ":" by ": " here to make tags with ":" possible. This
        # is needed to process logs generated by windows agent logfiles
        # like "c://test.log".
        tag, message = line.split(": ", 1)
        event["text"] = message.strip()

        if '[' in tag:
            app, pid = tag.split('[', 1)
            pid = pid.rstrip(']')
        else:
            app = tag
            pid = 0

        event["application"] = app
        event["pid"] = pid
        return event

    def parse_rfc5424_syslog_info(self, line):
        event = {}

        (_unused_version, timestamp, hostname, app_name, procid,
         _unused_msgid, rest) = line.split(" ", 6)

        # There is no 3339 parsing built into python. We do ignore subseconds and timezones
        # here. This is seems to be ok for the moment - sorry. Please drop a note if you
        # got a good solutuion for this.
        event['time'] = time.mktime(time.strptime(timestamp[:19], '%Y-%m-%dT%H:%M:%S'))

        if hostname != "-":
            event["host"] = hostname

        if app_name != "-":
            event["application"] = app_name

        if procid != "-":
            event["pid"] = procid

        if rest[0] == "[":
            # has stuctured data
            structured_data, message = rest[1:].split("] ", 1)
        elif rest.startswith("- "):
            # has no stuctured data
            structured_data, message = rest.split(" ", 1)
        else:
            raise Exception("Invalid RFC 5424 syslog message")

        if structured_data != "-":
            event["text"] = "[%s] %s" % (structured_data, message)
        else:
            event["text"] = message

        return event

    def parse_monitoring_info(self, line):
        event = {}
        # line starts with '@'
        if line[11] == ';':
            timestamp_str, sl, contact, rest = line[1:].split(';', 3)
            host, rest = rest.split(None, 1)
            if len(sl):
                event["sl"] = int(sl)
            if len(contact):
                event["contact"] = contact
        else:
            timestamp_str, host, rest = line[1:].split(None, 2)

        event["time"] = float(int(timestamp_str))
        service, message = rest.split(": ", 1)
        event["application"] = service
        event["text"] = message.strip()
        event["host"] = host
        return event

    # Translate a hostname if this is configured. We are
    # *really* sorry: this code snipped is copied from modules/check_mk_base.py.
    # There is still no common library. Please keep this in sync with the
    # original code
    def translate_hostname(self, backedhost):
        translation = self._config["hostname_translation"]

        # Here comes the original code from modules/check_mk_base.py
        if translation:
            # 1. Case conversion
            caseconf = translation.get("case")
            if caseconf == "upper":
                backedhost = backedhost.upper()
            elif caseconf == "lower":
                backedhost = backedhost.lower()

            # 2. Drop domain part (not applied to IP addresses!)
            if translation.get("drop_domain") and backedhost:
                # only apply if first part does not convert successfully into an int
                firstpart = backedhost.split(".", 1)[0]
                try:
                    int(firstpart)
                except Exception:
                    backedhost = firstpart

            # 3. Regular expression conversion
            if "regex" in translation:
                for regex, subst in translation["regex"]:
                    if not regex.endswith('$'):
                        regex += '$'
                    rcomp = cmk.regex.regex(regex)
                    mo = rcomp.match(backedhost)
                    if mo:
                        backedhost = subst
                        for nr, text in enumerate(mo.groups()):
                            backedhost = backedhost.replace("\\%d" % (nr + 1), text)
                        break

            # 4. Explicity mapping
            for from_host, to_host in translation.get("mapping", []):
                if from_host == backedhost:
                    backedhost = to_host
                    break

        return backedhost

    def do_translate_hostname(self, event):
        try:
            event["host"] = self.translate_hostname(event["host"])
        except Exception as e:
            if self._config["debug_rules"]:
                self._logger.exception('Unable to parse host "%s" (%s)' % (event.get("host"), e))
            event["host"] = ""

    def create_event_from_line(self, line, address):
        event = {
            # address is either None or a tuple of (ipaddress, port)
            "ipaddress": address and address[0] or "",
            "core_host": "",
            "host_in_downtime": False,
        }
        try:
            # Variant 1: plain syslog message without priority/facility:
            # May 26 13:45:01 Klapprechner CRON[8046]:  message....

            # Variant 1a: plain syslog message without priority/facility/host:
            # May 26 13:45:01 Klapprechner CRON[8046]:  message....

            # Variant 2: syslog message including facility (RFC 3164)
            # <78>May 26 13:45:01 Klapprechner CRON[8046]:  message....

            # Variant 3: local Nagios alert posted by mkevent -n
            # <154>@1341847712;5;Contact Info;  MyHost My Service: CRIT - This che

            # Variant 4: remote Nagios alert posted by mkevent -n -> syslog
            # <154>Jul  9 17:28:32 Klapprechner @1341847712;5;Contact Info;  MyHost My Service: CRIT - This che

            # Variant 5: syslog message
            #  Timestamp is RFC3339 with additional restrictions:
            #  - The "T" and "Z" characters in this syntax MUST be upper case.
            #  - Usage of the "T" character is REQUIRED.
            #  - Leap seconds MUST NOT be used.
            # <166>2013-04-05T13:49:31.685Z esx Vpxa: message....

            # Variant 6: syslog message without date / host:
            # <5>SYSTEM_INFO: [WLAN-1] Triggering Background Scan

            # Variant 7: logwatch.ec event forwarding
            # <78>@1341847712 Klapprechner /var/log/syslog: message....

            # Variant 7a: Event simulation
            # <%PRI%>@%TIMESTAMP%;%SL% %HOSTNAME% %syslogtag%: %msg%

            # Variant 8: syslog message from sophos firewall
            # <84>2015:03:25-12:02:06 gw pluto[7122]: listening for IKE messages

            # Variant 9: syslog message (RFC 5424)
            # <134>1 2016-06-02T12:49:05.181+02:00 chrissw7 ChrisApp - TestID - coming from  java code

            # Variant 10:
            # 2016 May 26 15:41:47 IST XYZ Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet45 (XXX.ASAD.Et45), changed state to up
            # year month day hh:mm:ss timezone HOSTNAME KeyAgent:

            # FIXME: Would be better to parse the syslog messages in another way:
            # Split the message by the first ":", then split the syslog header part
            # and detect which information are present. Take a look at the syslog RFCs
            # for details.

            # Variant 2,3,4,5,6,7,8
            if line.startswith('<'):
                i = line.find('>')
                prio = int(line[1:i])
                line = line[i + 1:]
                event["facility"] = prio >> 3
                event["priority"] = prio & 7

            # Variant 1,1a
            else:
                event["facility"] = 1  # user
                event["priority"] = 5  # notice

            # Variant 7 and 7a
            if line[0] == '@' and line[11] in [' ', ';']:
                details, event['host'], line = line.split(' ', 2)
                detail_tokens = details.split(';')
                timestamp = detail_tokens[0]
                if len(detail_tokens) > 1:
                    event["sl"] = int(detail_tokens[1])
                event['time'] = float(timestamp[1:])
                event.update(self.parse_syslog_info(line))

            # Variant 3
            elif line.startswith("@"):
                event.update(self.parse_monitoring_info(line))

            # Variant 5
            elif len(line) > 24 and line[10] == 'T':
                # There is no 3339 parsing built into python. We do ignore subseconds and timezones
                # here. This is seems to be ok for the moment - sorry. Please drop a note if you
                # got a good solutuion for this.
                rfc3339_part, event['host'], line = line.split(' ', 2)
                event['time'] = time.mktime(time.strptime(rfc3339_part[:19], '%Y-%m-%dT%H:%M:%S'))
                event.update(self.parse_syslog_info(line))

            # Variant 9
            elif len(line) > 24 and line[12] == "T":
                event.update(self.parse_rfc5424_syslog_info(line))

            # Variant 8
            elif line[10] == '-' and line[19] == ' ':
                event['host'] = line.split(' ')[1]
                event['time'] = time.mktime(time.strptime(line.split(' ')[0], '%Y:%m:%d-%H:%M:%S'))
                rest = " ".join(line.split(' ')[2:])
                event.update(self.parse_syslog_info(rest))

            # Variant 6
            elif len(line.split(': ', 1)[0].split(' ')) == 1:
                event.update(self.parse_syslog_info(line))
                # There is no datetime information in the message, use current time
                event['time'] = time.time()
                # There is no host information, use the provided address
                if address and type(address) == tuple:
                    event["host"] = address[0]

            # Variant 10
            elif line[4] == " " and line[:4].isdigit():
                time_part = line[:20]  # ignoring tz info
                event["host"], application, line = line[25:].split(" ", 2)
                event["application"] = application.rstrip(":")
                event["text"] = line
                event['time'] = time.mktime(time.strptime(time_part, '%Y %b %d %H:%M:%S'))

            # Variant 1,1a,2,4
            else:
                month_name, day, timeofday, rest = line.split(None, 3)

                # Special handling for variant 1a. Detect whether or not host
                # is a hostname or syslog tag
                host, tmp_rest = rest.split(None, 1)
                if host.endswith(":"):
                    # There is no host information sent, use the source address as "host"
                    host = address[0]
                else:
                    # Use the extracted host and continue with the remaining message text
                    rest = tmp_rest

                event["host"] = host

                # Variant 4
                if rest.startswith("@"):
                    event.update(self.parse_monitoring_info(rest))

                # Variant 1, 2
                else:
                    event.update(self.parse_syslog_info(rest))

                    month = EventServer.month_names[month_name]
                    day = int(day)

                    # Nasty: the year is not contained in the message. We cannot simply
                    # assume that the message if from the current year.
                    lt = time.localtime()
                    if lt.tm_mon < 6 and month > 6:  # Assume that message is from last year
                        year = lt.tm_year - 1
                    else:
                        year = lt.tm_year  # Assume the current year

                    hours, minutes, seconds = map(int, timeofday.split(":"))

                    # A further problem here: we do not now whether the message is in DST or not
                    event["time"] = time.mktime((year, month, day, hours, minutes, seconds, 0, 0, lt.tm_isdst))

            # The event simulator ships the simulated original IP address in the
            # hostname field, separated with a pipe, e.g. "myhost|1.2.3.4"
            if "|" in event["host"]:
                event["host"], event["ipaddress"] = event["host"].split("|", 1)

        except Exception as e:
            if self._config["debug_rules"]:
                self._logger.exception('Got non-syslog message "%s" (%s)' % (line, e))
            event = {
                "facility": 1,
                "priority": 0,
                "text": line,
                "host": "",
                "ipaddress": address and address[0] or "",
                "application": "",
                "pid": 0,
                "time": time.time(),
                "core_host": "",
                "host_in_downtime": False,
            }

        if self._config["debug_rules"]:
            self._logger.info('Parsed message:\n' +
                             ("".join([" %-15s %s\n" % (k + ":", v) for (k, v) in
                                       sorted(event.iteritems())])).rstrip())

        return event

    def log_message(self, event):
        try:
            with get_logfile(self._config, self.settings.paths.messages_dir.value).open(mode='ab') as f:
                f.write("%s %s %s%s: %s\n" % (
                    time.strftime("%b %d %H:%M:%S", time.localtime(event["time"])),
                    event["host"],
                    event["application"],
                    event["pid"] and ("[%s]" % event["pid"]) or "",
                    event["text"]))
        except Exception:
            if self.settings.options.debug:
                raise
            # Better silently ignore errors. We could have run out of
            # diskspace and make things worse by logging that we could
            # not log.

    def get_hosts_with_active_event_limit(self):
        hosts = []
        for hostname, num_existing_events in self._event_status.num_existing_events_by_host.iteritems():
            if num_existing_events >= self._config["event_limit"]["by_host"]["limit"]:
                hosts.append(hostname)
        return hosts

    def get_rules_with_active_event_limit(self):
        rule_ids = []
        for rule_id, num_existing_events in self._event_status.num_existing_events_by_rule.iteritems():
            if rule_id is None:
                continue  # Ignore rule unrelated overflow events. They have no rule id associated.
            if num_existing_events >= self._config["event_limit"]["by_rule"]["limit"]:
                rule_ids.append(rule_id)
        return rule_ids

    def is_overall_event_limit_active(self):
        return self._event_status.num_existing_events \
            >= self._config["event_limit"]["overall"]["limit"]

    # protected by lock_eventstatus
    def new_event_respecting_limits(self, event):
        self._logger.verbose("Checking limit for message from %s (rule '%s')" % (
            event["host"], event["rule_id"]))

        with lock_eventstatus:
            if self._handle_event_limit("overall", event):
                return False

            if self._handle_event_limit("by_host", event):
                return False

            if self._handle_event_limit("by_rule", event):
                return False

            self._event_status.new_event(self._table_events, event)
            return True

    # The following actions can be configured:
    # stop                 Stop creating new events
    # stop_overflow        Stop creating new events, create overflow event
    # stop_overflow_notify Stop creating new events, create overflow event, notfy
    # delete_oldest        Delete oldest event, create new event
    # protected by lock_eventstatus

    # Returns False if the event has been created and actions should be
    # performed on that event
    def _handle_event_limit(self, ty, event):
        assert ty in ["overall", "by_rule", "by_host"]

        num_already_open = self._event_status.get_num_existing_events_by(ty, event)
        limit, action = self._get_event_limit(ty, event)
        self._logger.verbose("  Type: %s, already open events: %d, Limit: %d" % (ty, num_already_open, limit))

        # Limit not reached: add new event
        if num_already_open < limit:
            num_already_open += 1  # after adding this event

        # Limit even then still not reached: we are fine
        if num_already_open < limit:
            return False

        # Delete oldest messages if that is the configure method of keeping the limit
        if action == "delete_oldest":
            while num_already_open > limit:
                self._perfcounters.count("overflows")
                self._event_status.remove_oldest_event(ty, event)
                num_already_open -= 1
            return False

        # Limit reached already in the past: Simply drop silently
        if num_already_open > limit:
            # Just log in verbose mode! Otherwise log file will be flooded
            self._logger.verbose("  Skip processing because limit is already in effect")
            self._perfcounters.count("overflows")
            return True  # Prevent creation and prevent one time actions (below)

        self._logger.info("  The %s limit has been reached" % ty)

        # This is the event which reached the limit, allow creation of it. Further
        # events will be stopped.

        # Perform one time actions
        overflow_event = self._create_overflow_event(ty, event, limit)

        if "overflow" in action:
            self._logger.info("  Creating overflow event")
            self._event_status.new_event(self._table_events, overflow_event)

        if "notify" in action:
            self._logger.info("  Creating overflow notification")
            do_notify(self, overflow_event)

        return False

    # protected by lock_eventstatus
    def _get_event_limit(self, ty, event):
        # Prefer the rule individual limit for by_rule limit (in case there is some)
        if ty == "by_rule":
            rule_limit = self._rule_by_id[event["rule_id"]].get("event_limit")
            if rule_limit:
                return rule_limit["limit"], rule_limit["action"]

        # Prefer the host individual limit for by_host limit (in case there is some)
        if ty == "by_host":
            host_config = self.host_config.get(event["core_host"], {})
            host_limit = host_config.get("custom_variables", {}).get("EC_EVENT_LIMIT")
            if host_limit:
                limit, action = host_limit.split(":", 1)
                return int(limit), action

        limit = self._config["event_limit"][ty]["limit"]
        action = self._config["event_limit"][ty]["action"]

        return limit, action

    def _create_overflow_event(self, ty, event, limit):
        now = time.time()
        new_event = {
            "rule_id": None,
            "phase": "open",
            "count": 1,
            "time": now,
            "first": now,
            "last": now,
            "comment": "",
            "host": "",
            "ipaddress": "",
            "application": "Event Console",
            "pid": 0,
            "priority": 2,  # crit
            "facility": 1,  # user
            "match_groups": (),
            "match_groups_syslog_application": (),
            "state": 2,  # crit
            "sl": event["sl"],
            "core_host": "",
            "host_in_downtime": False,
        }
        self._add_rule_contact_groups_to_event({}, new_event)

        if ty == "overall":
            new_event["text"] = (
                "The overall event limit of %d open events has been reached. Not "
                "opening any additional event until open events have been "
                "archived." % limit
            )

        elif ty == "by_host":
            new_event.update({
                "host": event["host"],
                "ipaddress": event["ipaddress"],
                "text": (
                    "The host event limit of %d open events has been reached for host \"%s\". "
                    "Not opening any additional event for this host until open events have "
                    "been archived." % (limit, event["host"])
                )
            })

            # Lookup the monitoring core hosts and add the core host
            # name to the event when one can be matched
            self._add_core_host_to_new_event(new_event)

        elif ty == "by_rule":
            new_event.update({
                "rule_id": event["rule_id"],
                "contact_groups": event["contact_groups"],
                "contact_groups_notify": event.get("contact_groups_notify", False),
                "contact_groups_precedence": event.get("contact_groups_precedence", "host"),
                "text": (
                    "The rule event limit of %d open events has been reached for rule \"%s\". "
                    "Not opening any additional event for this rule until open events have "
                    "been archived." %
                    (limit, event["rule_id"])
                )
            })

        else:
            raise NotImplementedError()

        return new_event


#.
#   .--Status Queries------------------------------------------------------.
#   |  ____  _        _                ___                  _              |
#   | / ___|| |_ __ _| |_ _   _ ___   / _ \ _   _  ___ _ __(_) ___  ___    |
#   | \___ \| __/ _` | __| | | / __| | | | | | | |/ _ \ '__| |/ _ \/ __|   |
#   |  ___) | || (_| | |_| |_| \__ \ | |_| | |_| |  __/ |  | |  __/\__ \   |
#   | |____/ \__\__,_|\__|\__,_|___/  \__\_\\__,_|\___|_|  |_|\___||___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Parsing and processing of status queries                             |
#   '----------------------------------------------------------------------'

class Queries(object):
    def __init__(self, status_server, sock):
        super(Queries, self).__init__()
        self._status_server = status_server
        self._socket = sock
        self._buffer = ""

    def __iter__(self):
        return self

    def next(self):
        while True:
            parts = self._buffer.split("\n\n", 1)
            if len(parts) > 1:
                break
            data = self._socket.recv(4096)
            if len(data) == 0:
                if len(self._buffer) == 0:
                    raise StopIteration()
                parts = [self._buffer, ""]
                break
            self._buffer += data
        request, self._buffer = parts

        request_lines = request.decode("utf-8").splitlines()

        cls = Query.get_query_class(request_lines)
        return cls(self._status_server, request_lines)


class Query(object):
    _allowed_methods = set(["GET", "REPLICATE", "COMMAND"])
    _allowed_formats = set(["python", "plain", "json"])
    _allowed_headers = set(["OutputFormat", "Filter", "Columns", "Limit"])

    @classmethod
    def get_query_class(cls, raw_query):
        parts = raw_query[0].split(None, 1)
        if len(parts) != 2:
            raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")

        method = parts[0]

        if method not in cls._allowed_methods:
            raise MKClientError("Invalid method %s (allowed are %s) " %
                                (method, ", ".join(cls._allowed_methods)))

        # TODO: This is pure maintenance horror! Never ever calculate the name
        # of a class in user code...
        return globals()["Query%s" % method]

    def __init__(self, status_server, raw_query):
        super(Query, self).__init__()

        self._logger = logger
        self.output_format = "python"

        self._raw_query = raw_query
        self._from_raw_query(status_server)

    def _from_raw_query(self, status_server):
        self._parse_method_and_args()

    def _parse_method_and_args(self):
        parts = self._raw_query[0].split(None, 1)
        if len(parts) != 2:
            raise MKClientError("Invalid query. Need GET/COMMAND plus argument(s)")

        self.method, self.method_arg = parts

    def __repr__(self):
        return repr("\n".join(self._raw_query))


class QueryGET(Query):
    _allowed_tables = set(["events", "history", "rules", "status"])

    def _from_raw_query(self, status_server):
        super(QueryGET, self)._from_raw_query(status_server)
        self._parse_table(status_server)
        self._parse_header_lines()

    def _parse_table(self, status_server):
        self.table_name = self.method_arg

        if self.table_name not in self._allowed_tables:
            raise MKClientError("Invalid table: %s (allowed are: %s)" %
                                (self.table_name, ", ".join(self._allowed_tables)))

        self.table = status_server.table(self.table_name)

    def _parse_header_lines(self):
        self.requested_columns = self.table.column_names  # use all columns as default
        self.filters = []
        self.limit = None
        self.only_host = None

        self.header_lines = []
        for line in self._raw_query[1:]:
            try:
                header, argument = line.rstrip("\n").split(":", 1)
                argument = argument.lstrip(" ")

                # TODO: Be compatible with livestatus: Only log the issue to the log
                #if header not in self._allowed_headers:
                #    raise MKClientError("Invalid header: \"%s\" (allowed are %s)" %
                #                                ", ".join(self._allowed_headers))

                if header == "OutputFormat":
                    if argument not in self._allowed_formats:
                        raise MKClientError("Invalid output format \"%s\" (allowed are: %s)" %
                                            (argument, ", ".join(self._allowed_formats)))

                    self.output_format = argument

                elif header == "Columns":
                    self.requested_columns = argument.split(" ")

                elif header == "Filter":
                    name, opfunc, argument = self._parse_filter(argument)

                    # Needed for later optimization (check_mkevents)
                    if name == "event_host" and opfunc == filter_operators['in']:
                        self.only_host = set(argument)

                    self.filters.append((name, opfunc, argument))

                elif header == "Limit":
                    self.limit = int(argument)

                else:
                    self._logger.info("Ignoring not-implemented header %s" % header)

            except Exception as e:
                raise MKClientError("Invalid header line '%s': %s" % (line.rstrip(), e))

    def _parse_filter(self, textspec):
        # Examples:
        # id = 17
        # name ~= This is some .* text
        # host_name =
        parts = textspec.split(None, 2)
        if len(parts) == 2:
            parts.append("")
        column, operator, argument = parts

        try:
            convert = self.table.column_types[column]
        except KeyError:
            raise MKClientError("Unknown column: %s (Available are: %s)" %
                                (column, self.table.column_names))

        # TODO: BUG: The query is decoded to unicode after receiving it from
        # the socket. The columns with type str (initialied with "") will apply
        # str(argument) here and convert the value back to str! This will crash
        # when the filter contains non ascii characters!
        # Fix this by making the default values unicode and skip unicode conversion
        # here (for performance reasons) because argument is already unicode.
        if operator == 'in':
            argument = map(convert, argument.split())
        else:
            argument = convert(argument)

        opfunc = filter_operators.get(operator)
        if not opfunc:
            raise MKClientError("Unknown filter operator '%s'" % operator)

        return (column, opfunc, argument)

    def requested_column_indexes(self):
        indexes = []

        for column_name in self.requested_columns:
            try:
                column_index = self.table.column_indices[column_name]
            except KeyError:
                # The column is not known: Use None as index and None value later
                column_index = None
            indexes.append(column_index)

        return indexes


class QueryREPLICATE(Query):
    pass


class QueryCOMMAND(Query):
    pass


#.
#   .--Status Tables-------------------------------------------------------.
#   |     ____  _        _               _____     _     _                 |
#   |    / ___|| |_ __ _| |_ _   _ ___  |_   _|_ _| |__ | | ___  ___       |
#   |    \___ \| __/ _` | __| | | / __|   | |/ _` | '_ \| |/ _ \/ __|      |
#   |     ___) | || (_| | |_| |_| \__ \   | | (_| | |_) | |  __/\__ \      |
#   |    |____/ \__\__,_|\__|\__,_|___/   |_|\__,_|_.__/|_|\___||___/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Definitions of the tables available for status queries               |
#   '----------------------------------------------------------------------'
# If you need a new column here, then these are the places to change:
# bin/mkeventd:
# - add column to the end of StatusTableEvents.columns
# - add column to grepping_filters if it is a str column
# - deal with convert_history_line() (if not a str column)
# - make sure that the new column is filled at *every* place where
#   an event is being created:
#   * create_event_from_trap()
#   * create_event_from_line()
#   * _handle_absent_event()
#   * _create_overflow_event()
# - When loading the status file add the possibly missing column to all
#   loaded events (load_status())
# - Maybe add matching/rewriting for the new column
# - write the actual code using the new column
# web:
# - Add column painter for the new column
# - Create a sorter
# - Create a filter
# - Add painter and filter to all views where appropriate
# - maybe add WATO code for matching rewriting
# - do not forget event_rule_matches() in web!
# - maybe add a field into the event simulator


class StatusTable(object):
    prefix = None
    columns = []

    # Must return a enumerable type containing fully populated lists (rows) matching the
    # columns of the table
    @abc.abstractmethod
    def _enumerate(self, query):
        raise NotImplementedError()

    def __init__(self):
        super(StatusTable, self).__init__()
        self._logger = logger.getChild("status_table.%s" % self.prefix)
        self._populate_column_views()

    def _populate_column_views(self):
        self.column_names = [c[0] for c in self.columns]
        self.column_defaults = dict(self.columns)

        self.column_types = {}
        for name, def_val in self.columns:
            self.column_types[name] = type(def_val)

        self.column_indices = dict([(name, index) for index, name
                                    in enumerate(self.column_names)])


    def query(self, query):
        requested_column_indexes = query.requested_column_indexes()

        # Output the column headers
        # TODO: Add support for ColumnHeaders like in livestatus?
        yield query.requested_columns

        num_rows = 0
        for row in self._enumerate(query):
            if query.limit is not None and num_rows >= query.limit:
                break  # The maximum number of rows has been reached

            # Apply filters
            # TODO: History filtering is done in history load code. Check for improvements
            if query.filters and query.table_name != "history":
                match = self.filter_row(query, row)
                if not match:
                    continue

            yield self._build_result_row(row, requested_column_indexes)
            num_rows += 1

    def _build_result_row(self, row, requested_column_indexes):
        result_row = []
        for index in requested_column_indexes:
            if index is None:
                result_row.append(None)
            else:
                result_row.append(row[index])
        return result_row

    def filter_row(self, query, row):
        for column, opfunc, argument in query.filters:
            if not opfunc(row[query.table.column_indices[column]], argument):
                return None
        return row


class StatusTableEvents(StatusTable):
    prefix = "event"
    columns = [
        ("event_id", 1),
        ("event_count", 1),
        ("event_text", ""),
        ("event_first", 0.0),
        ("event_last", 0.0),
        ("event_comment", ""),
        ("event_sl", 0),  # filter fehlt
        ("event_host", ""),
        ("event_contact", ""),
        ("event_application", ""),
        ("event_pid", 0),
        ("event_priority", 5),
        ("event_facility", 1),
        ("event_rule_id", ""),
        ("event_state", 0),
        ("event_phase", ""),
        ("event_owner", ""),
        ("event_match_groups", ""),  # last column up to 1.2.4
        ("event_contact_groups", ""),  # introduced in 1.2.5i2
        ("event_ipaddress", ""),  # introduced in 1.2.7i1
        ("event_orig_host", ""),  # introduced in 1.4.0b1
        ("event_contact_groups_precedence", "host"),  # introduced in 1.4.0b1
        ("event_core_host", ""),  # introduced in 1.5.0i1
        ("event_host_in_downtime", False),  # introduced in 1.5.0i1
        ("event_match_groups_syslog_application", ""),  # introduced in 1.5.0i2
    ]

    def __init__(self, event_status):
        super(StatusTableEvents, self).__init__()
        self._event_status = event_status

    def _enumerate(self, query):
        for event in self._event_status.get_events():
            # Optimize filters that are set by the check_mkevents active check. Since users
            # may have a lot of those checks running, it is a good idea to optimize this.
            if query.only_host and event["host"] not in query.only_host:
                continue

            row = []
            for column_name in self.column_names:
                try:
                    row.append(event[column_name[6:]])
                except KeyError:
                    # The row does not have this value. Use the columns default value
                    row.append(self.column_defaults[column_name])

            yield row


class StatusTableHistory(StatusTable):
    prefix = "history"
    columns = [
        ("history_line", 0),  # Line number in event history file
        ("history_time", 0.0),
        ("history_what", ""),
        ("history_who", ""),
        ("history_addinfo", ""),
    ] + StatusTableEvents.columns

    def __init__(self, settings, config, table_events, logger):
        super(StatusTableHistory, self).__init__()
        self.settings = settings
        self._config = config
        self._table_events = table_events
        self._logger = logger

    def _enumerate(self, query):
        if self._config['archive_mode'] == 'mongodb':
            return get_event_history_from_mongodb(self.settings, self._table_events, query)
        else:
            return get_event_history_from_file(self.settings, self, self._logger, query)


class StatusTableRules(StatusTable):
    prefix = "rule"
    columns = [
        ("rule_id", ""),
        ("rule_hits", 0),
    ]

    def __init__(self, event_status):
        super(StatusTableRules, self).__init__()
        self._event_status = event_status

    def _enumerate(self, query):
        return self._event_status.get_rule_stats()


class StatusTableStatus(StatusTable):
    prefix = "status"
    columns = EventServer.status_columns()

    def __init__(self, event_server):
        super(StatusTableStatus, self).__init__()
        self._event_server = event_server

    def _enumerate(self, query):
        return self._event_server.get_status()


#.
#   .--StatusServer--------------------------------------------------------.
#   |     ____  _        _             ____                                |
#   |    / ___|| |_ __ _| |_ _   _ ___/ ___|  ___ _ ____   _____ _ __      |
#   |    \___ \| __/ _` | __| | | / __\___ \ / _ \ '__\ \ / / _ \ '__|     |
#   |     ___) | || (_| | |_| |_| \__ \___) |  __/ |   \ V /  __/ |        |
#   |    |____/ \__\__,_|\__|\__,_|___/____/ \___|_|    \_/ \___|_|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Beantworten von Status- und Kommandoanfragen über das UNIX-Socket   |
#   '----------------------------------------------------------------------'

class StatusServer(ECServerThread):
    def __init__(self, settings, config, slave_status, perfcounters, event_status, event_server, table_events, terminate_main_event):
        super(StatusServer, self).__init__(name="StatusServer",
                                           settings=settings,
                                           config=config,
                                           slave_status=slave_status,
                                           table_events=table_events,
                                           profiling_enabled=settings.options.profile_status,
                                           profile_file=settings.paths.status_server_profile.value)
        self._socket = None
        self._tcp_socket = None
        self._reopen_sockets = False

        self.table_events = table_events # alias for reflection Kung Fu :-P
        self.table_history = StatusTableHistory(settings, config, table_events, self._logger)
        self.table_rules = StatusTableRules(event_status)
        self.table_status = StatusTableStatus(event_server)
        self._perfcounters = perfcounters
        self._event_status = event_status
        self._event_server = event_server
        self._terminate_main_event = terminate_main_event

        self.open_unix_socket()
        self.open_tcp_socket()

    def table(self, name):
        return getattr(self, "table_%s" % name)

    def open_unix_socket(self):
        path = self.settings.paths.unix_socket.value
        if path.exists():
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(str(path))
        # Make sure that socket is group writable
        path.chmod(0o664)
        self._socket.listen(self._config['socket_queue_len'])
        self._unix_socket_queue_len = self._config['socket_queue_len']  # detect changes in config

    def open_tcp_socket(self):
        if self._config["remote_status"]:
            try:
                self._tcp_port, self._tcp_allow_commands = self._config["remote_status"][:2]
                try:
                    self._tcp_access_list = self._config["remote_status"][2]
                except Exception:
                    self._tcp_access_list = None

                self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._tcp_socket.bind(("0.0.0.0", self._tcp_port))
                self._tcp_socket.listen(self._config['socket_queue_len'])
                self._logger.info("Going to listen for status queries on TCP port %d" % self._tcp_port)
            except Exception as e:
                if self.settings.options.debug:
                    raise
                self._logger.exception("Cannot listen on TCP socket port %d: %s" %
                                      (self._tcp_port, e))
        else:
            self._tcp_socket = None
            self._tcp_port = 0
            self._tcp_allow_commands = False
            self._tcp_access_list = None

    def close_unix_socket(self):
        if self._socket:
            self._socket.close()
            self._socket = None

    def close_tcp_socket(self):
        if self._tcp_socket:
            self._tcp_socket.close()
            self._tcp_socket = None

    def reopen_sockets(self):
        if self._unix_socket_queue_len != self._config["socket_queue_len"]:
            self._logger.info("socket_queue_len has changed. Reopening UNIX socket.")
            self.close_unix_socket()
            self.open_unix_socket()

        self.close_tcp_socket()
        self.open_tcp_socket()

    def reload_configuration(self, config):
        self._config = config
        self._reopen_sockets = True

    def serve(self):
        while not self._shal_terminate():
            try:
                client_socket = None
                addr_info = None

                if self._reopen_sockets:
                    self.reopen_sockets()
                    self._reopen_sockets = False

                listen_list = [self._socket]
                if self._tcp_socket:
                    listen_list.append(self._tcp_socket)

                try:
                    readable = select.select(listen_list, [], [], 0.2)[0]
                except select.error as e:
                    if e[0] == errno.EINTR:
                        continue
                    raise

                for s in readable:
                    client_socket, addr_info = s.accept()
                    client_socket.settimeout(3)
                    before = time.time()
                    self._perfcounters.count("connects")
                    if addr_info:
                        allow_commands = self._tcp_allow_commands
                        if self.settings.options.debug:
                            self._logger.info("Handle status connection from %s:%d" % addr_info)
                        if self._tcp_access_list is not None and addr_info[0] not in \
                           self._tcp_access_list:
                            client_socket.close()
                            client_socket = None
                            self._logger.info("Denying access to status socket from %s (allowed is only %s)" %
                                             (addr_info[0], ", ".join(self._tcp_access_list)))
                            continue
                    else:
                        allow_commands = True

                    self.handle_client(client_socket, allow_commands,
                                       addr_info and addr_info[0] or "")

                    duration = time.time() - before
                    self._logger.verbose("Answered request in %0.2f ms" % (duration * 1000))
                    self._perfcounters.count_time("request", duration)

            except Exception as e:
                msg = "Error handling client %s: %s" % (addr_info, e)
                # Do not log a stack trace for client errors, they are not *our* fault.
                if isinstance(e, MKClientError):
                    self._logger.error(msg)
                else:
                    self._logger.exception(msg)
                if client_socket:
                    client_socket.close()
                    client_socket = None
                time.sleep(0.2)
            client_socket = None  # close without danger of exception

    def handle_client(self, client_socket, allow_commands, client_ip):
        for query in Queries(self, client_socket):
            self._logger.verbose("Client livestatus query: %r" % query)

            with lock_eventstatus:
                if query.method == "GET":
                    response = self.table(query.table_name).query(query)

                elif query.method == "REPLICATE":
                    response = self.handle_replicate(query.method_arg, client_ip)

                elif query.method == "COMMAND":
                    if not allow_commands:
                        raise MKClientError("Sorry. Commands are disallowed via TCP")
                    self.handle_command_request(query.method_arg)
                    response = None

                else:
                    raise NotImplementedError()

                try:
                    self._answer_query(client_socket, query, response)
                except socket.error as e:
                    if e.errno == 32:  # Broken pipe -> ignore this
                        pass
                    else:
                        raise

        client_socket.close()

    # Only GET queries have customizable output formats. COMMAND is always
    # a dictionay and COMMAND is always None and always output as "python"
    def _answer_query(self, client_socket, query, response):
        if query.method != "GET":
            self._answer_query_python(client_socket, response)
            return

        if query.output_format == "plain":
            for row in response:
                client_socket.sendall("\t".join([quote_tab(c) for c in row]) + "\n")

        elif query.output_format == "json":
            client_socket.sendall(json.dumps(list(response)) + "\n")

        elif query.output_format == "python":
            self._answer_query_python(client_socket, list(response))

        else:
            raise NotImplementedError()

    def _answer_query_python(self, client_socket, response):
        client_socket.sendall(repr(response) + "\n")

    # All commands are already locked with lock_eventstatus
    def handle_command_request(self, commandline):
        self._logger.info("Executing command: %s" % commandline)
        parts = commandline.split(";")
        command = parts[0]
        replication_allow_command(self._config, command, self._slave_status)
        arguments = parts[1:]
        if command == "DELETE":
            self.handle_command_delete(arguments)
        elif command == "RELOAD":
            self.handle_command_reload()
        elif command == "SHUTDOWN":
            self._logger.info("Going to shut down")
            terminate(self._terminate_main_event, self._event_server, self)
        elif command == "REOPENLOG":
            self.handle_command_reopenlog()
        elif command == "FLUSH":
            self.handle_command_flush()
        elif command == "SYNC":
            self.handle_command_sync()
        elif command == "RESETCOUNTERS":
            self.handle_command_resetcounters(arguments)
        elif command == "UPDATE":
            self.handle_command_update(arguments)
        elif command == "CREATE":
            self.handle_command_create(arguments)
        elif command == "CHANGESTATE":
            self.handle_command_changestate(arguments)
        elif command == "ACTION":
            self.handle_command_action(arguments)
        elif command == "SWITCHMODE":
            self.handle_command_switchmode(arguments)
        else:
            raise MKClientError("Unknown command %s" % command)

    def handle_command_delete(self, arguments):
        if len(arguments) != 2:
            raise MKClientError("Wrong number of arguments for DELETE")
        event_id, user = arguments
        self._event_status.delete_event(self._table_events, int(event_id), user)

    def handle_command_update(self, arguments):
        event_id, user, acknowledged, comment, contact = arguments
        event = self._event_status.event(int(event_id))
        if not event:
            raise MKClientError("No event with id %s" % event_id)
        # Note the common practice: We validate parameters *before* doing any changes.
        if acknowledged:
            ack = int(acknowledged)
            if ack and event["phase"] not in ["open", "ack"]:
                raise MKClientError("You cannot acknowledge an event that is not open.")
            event["phase"] = "ack" if ack else "open"
        if comment:
            event["comment"] = comment
        if contact:
            event["contact"] = contact
        if user:
            event["owner"] = user
        log_event_history(self.settings, self._config, self._table_events, event, "UPDATE", user)

    def handle_command_create(self, arguments):
        # Would rather use process_raw_line(), but we are already
        # holding lock_eventstatus and it's sub functions are setting
        # lock_eventstatus too. The lock can not be allocated twice.
        # TODO: Change the lock type in future?
        # process_raw_lines("%s" % ";".join(arguments))
        with file(str(self.settings.paths.event_pipe.value), "w") as pipe:
            pipe.write(("%s\n" % ";".join(arguments)).encode("utf-8"))

    def handle_command_changestate(self, arguments):
        event_id, user, newstate = arguments
        event = self._event_status.event(int(event_id))
        if not event:
            raise MKClientError("No event with id %s" % event_id)
        event["state"] = int(newstate)
        if user:
            event["owner"] = user
        log_event_history(self.settings, self._config, self._table_events, event, "CHANGESTATE", user)

    def handle_command_reload(self):
        reload_configuration(self.settings, self._event_status, self._event_server, self, self._slave_status)

    def handle_command_reopenlog(self):
        self._logger.info("Closing this logfile")
        cmk.log.open_log(str(self.settings.paths.log_file.value))
        self._logger.info("Opened new logfile")

    # Erase our current state and history!
    def handle_command_flush(self):
        flush_event_history(self.settings, self._config)
        self._event_status.flush()
        self._event_status.save_status()
        if is_replication_slave(self._config):
            try:
                self.settings.paths.master_config_file.value.unlink()
                self.settings.paths.slave_status_file.value.unlink()
                update_slave_status(self._slave_status, self.settings, self._config)
            except Exception:
                pass
        self._logger.info("Flushed current status and historic events.")

    def handle_command_sync(self):
        self._event_status.save_status()

    def handle_command_resetcounters(self, arguments):
        if arguments:
            rule_id = arguments[0]
            self._logger.info("Resetting counters of rule " + rule_id)
        else:
            rule_id = None  # Reset all rule counters
            self._logger.info("Resetting all rule counters")
        self._event_status.reset_counters(rule_id)

    def handle_command_action(self, arguments):
        event_id, user, action_id = arguments
        event = self._event_status.event(int(event_id))
        if user:
            event["owner"] = user

        if action_id == "@NOTIFY":
            do_notify(self._event_server, event, user, is_cancelling=False)
        else:
            with lock_configuration:
                if action_id not in self._config["action"]:
                    raise MKClientError("The action '%s' is not defined. After adding new commands please "
                                        "make sure that you activate the changes in the Event Console." % action_id)
                action = self._config["action"][action_id]
            do_event_action(self.settings, self._config, self._table_events, action, event, user)

    def handle_command_switchmode(self, arguments):
        new_mode = arguments[0]
        if not is_replication_slave(self._config):
            raise MKClientError("Cannot switch replication mode: this is not a replication slave.")
        elif new_mode not in ["sync", "takeover"]:
            raise MKClientError("Invalid target mode '%s': allowed are only 'sync' and 'takeover'" %
                                new_mode)
        self._slave_status["mode"] = new_mode
        save_slave_status(self.settings, self._slave_status)
        self._logger.info("Switched replication mode to '%s' by external command." % new_mode)

    def handle_replicate(self, argument, client_ip):
        # Last time our slave got a config update
        try:
            last_update = int(argument)
            if self.settings.options.debug:
                self._logger.info("Replication: sync request from %s, last update %d seconds ago" % (
                    client_ip, time.time() - last_update))

        except Exception:
            raise MKClientError("Invalid arguments to command REPLICATE")
        return replication_send(self._config, self._event_status, last_update)


#.
#   .--Dispatching---------------------------------------------------------.
#   |         ____  _                 _       _     _                      |
#   |        |  _ \(_)___ _ __   __ _| |_ ___| |__ (_)_ __   __ _          |
#   |        | | | | / __| '_ \ / _` | __/ __| '_ \| | '_ \ / _` |         |
#   |        | |_| | \__ \ |_) | (_| | || (__| | | | | | | | (_| |         |
#   |        |____/|_|___/ .__/ \__,_|\__\___|_| |_|_|_| |_|\__, |         |
#   |                    |_|                                |___/          |
#   +----------------------------------------------------------------------+
#   |  Starten und Verwalten der beiden Threads.                           |
#   '----------------------------------------------------------------------'

def run_eventd(terminate_main_event, settings, config, perfcounters, event_status, event_server, status_server, slave_status):
    status_server.start()
    event_server.start()
    now = time.time()
    next_housekeeping = now + config["housekeeping_interval"]
    next_retention = now + config["retention_interval"]
    next_statistics = now + config["statistics_interval"]
    next_replication = 0  # force immediate replication after restart

    while not terminate_main_event.is_set():
        try:
            try:
                # Wait until either housekeeping or retention is due, but at
                # maximum 60 seconds. That way changes of the interval from a very
                # high to a low value will never require more than 60 seconds

                event_list = [next_housekeeping, next_retention, next_statistics]
                if is_replication_slave(config):
                    event_list.append(next_replication)

                time_left = max(0, min(event_list) - time.time())
                time.sleep(min(time_left, 60))

                now = time.time()
                if now > next_housekeeping:
                    event_server.do_housekeeping()
                    next_housekeeping = now + config["housekeeping_interval"]

                if now > next_retention:
                    with lock_eventstatus:
                        event_status.save_status()
                    next_retention = now + config["retention_interval"]

                if now > next_statistics:
                    perfcounters.do_statistics()
                    next_statistics = now + config["statistics_interval"]

                # Beware: replication might be turned on during this loop!
                if is_replication_slave(config) and now > next_replication:
                    replication_pull(settings, config, perfcounters, event_status, event_server, slave_status)
                    next_replication = now + config["replication"]["interval"]
            except MKSignalException as e:
                raise e
            except Exception as e:
                logger.exception("Exception in main thread:\n%s" % e)
                if settings.options.debug:
                    raise
                time.sleep(1)
        except MKSignalException as e:
            if e._signum == 1:
                logger.info("Received SIGHUP - going to reload configuration")
                reload_configuration(settings, event_status, event_server, status_server, slave_status)
            else:
                logger.info("Signalled to death by signal %d" % e._signum)
                terminate(terminate_main_event, event_server, status_server)

    # Now wait for termination of the server threads
    event_server.join()
    status_server.join()


#.
#   .--EventStatus---------------------------------------------------------.
#   |       _____                 _   ____  _        _                     |
#   |      | ____|_   _____ _ __ | |_/ ___|| |_ __ _| |_ _   _ ___         |
#   |      |  _| \ \ / / _ \ '_ \| __\___ \| __/ _` | __| | | / __|        |
#   |      | |___ \ V /  __/ | | | |_ ___) | || (_| | |_| |_| \__ \        |
#   |      |_____| \_/ \___|_| |_|\__|____/ \__\__,_|\__|\__,_|___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Bereithalten des aktuellen Event-Status. Dieser schützt sich selbst  |
#   | durch ein Lock vor gleichzeitigen Zugriffen durch die Threads.       |
#   '----------------------------------------------------------------------'

class EventStatus(object):

    def __init__(self, settings, config, perfcounters):
        self._logger = logger.getChild("EventStatus")
        self.settings = settings
        self._config = config
        self._perfcounters = perfcounters
        self.flush()

    def reload_configuration(self, config):
        self._config = config

    def flush(self):
        self._events = []
        self._next_event_id = 1
        self._rule_stats = {}
        self._interval_starts = {}  # needed for expecting rules
        self._initialize_event_limit_status()

        # TODO: might introduce some performance counters, like:
        # - number of received messages
        # - number of rule hits
        # - number of rule misses

    def events(self):
        return self._events

    def event(self, id):
        for event in self._events:
            if event["id"] == id:
                return event

    # Return beginning of current expectation interval. For new rules
    # we start with the next interval in future.
    def interval_start(self, rule_id, interval):
        if rule_id not in self._interval_starts:
            start = self.next_interval_start(interval, time.time())
            self._interval_starts[rule_id] = start
            return start
        else:
            start = self._interval_starts[rule_id]
            # Make sure that if the user switches from day to hour and we
            # are still waiting for the first interval to begin, that we
            # do not wait for the next day.
            next = self.next_interval_start(interval, time.time())
            if start > next:
                start = next
                self._interval_starts[rule_id] = start
            return start

    def next_interval_start(self, interval, previous_start):
        if type(interval) == tuple:
            length, offset = interval
            offset *= 3600
        else:
            length = interval
            offset = 0

        previous_start -= offset  # take into account timezone offset
        full_parts = divmod(previous_start, length)[0]
        next_start = (full_parts + 1) * length
        next_start += offset
        return next_start

    def start_next_interval(self, rule_id, interval):
        current_start = self.interval_start(rule_id, interval)
        next_start = self.next_interval_start(interval, current_start)
        self._interval_starts[rule_id] = next_start
        self._logger.debug("Rule %s: next interval starts %s (i.e. now + %.2f sec)" %
                          (rule_id, next_start, time.time() - next_start))

    def pack_status(self):
        return {
            "next_event_id": self._next_event_id,
            "events": self._events,
            "rule_stats": self._rule_stats,
            "interval_starts": self._interval_starts,
        }

    def unpack_status(self, status):
        self._next_event_id = status["next_event_id"]
        self._events = status["events"]
        self._rule_stats = status["rule_stats"]
        self._interval_starts = status["interval_starts"]

    def save_status(self):
        now = time.time()
        status = self.pack_status()
        path = self.settings.paths.status_file.value
        path_new = path.parent / (path.name + '.new')
        # Believe it or not: cPickle is more than two times slower than repr()
        with path_new.open(mode='wb') as f:
            f.write(repr(status) + "\n")
            f.flush()
            os.fsync(f.fileno())
        path_new.rename(path)
        elapsed = time.time() - now
        self._logger.verbose("Saved event state to %s in %.3fms." % (path, elapsed * 1000))

    def reset_counters(self, rule_id):
        if rule_id:
            if rule_id in self._rule_stats:
                del self._rule_stats[rule_id]
        else:
            self._rule_stats = {}
        self.save_status()

    def load_status(self, event_server):
        path = self.settings.paths.status_file.value
        if path.exists():
            try:
                status = ast.literal_eval(path.read_bytes())
                self._next_event_id = status["next_event_id"]
                self._events = status["events"]
                self._rule_stats = status["rule_stats"]
                self._interval_starts = status.get("interval_starts", {})
                self._initialize_event_limit_status()
                self._logger.info("Loaded event state from %s." % path)
            except Exception as e:
                self._logger.exception("Error loading event state from %s: %s" % (path, e))
                raise

        # Add new columns
        for event in self._events:
            event.setdefault("ipaddress", "")

            if "core_host" not in event:
                event_server.add_core_host_to_event(event)
                event["host_in_downtime"] = False

    # Called on Event Console initialization from status file to initialize
    # the current event limit state -> Sets internal counters which are
    # updated during runtime.
    def _initialize_event_limit_status(self):
        self.num_existing_events = len(self._events)

        self.num_existing_events_by_host = {}
        self.num_existing_events_by_rule = {}
        for event in self._events:
            self._count_event_add(event)

    def _count_event_add(self, event):
        if event["host"] not in self.num_existing_events_by_host:
            self.num_existing_events_by_host[event["host"]] = 1
        else:
            self.num_existing_events_by_host[event["host"]] += 1

        if event["rule_id"] not in self.num_existing_events_by_rule:
            self.num_existing_events_by_rule[event["rule_id"]] = 1
        else:
            self.num_existing_events_by_rule[event["rule_id"]] += 1

    def _count_event_remove(self, event):
        self.num_existing_events -= 1
        self.num_existing_events_by_host[event["host"]] -= 1
        self.num_existing_events_by_rule[event["rule_id"]] -= 1

    def new_event(self, table_events, event):
        self._perfcounters.count("events")
        event["id"] = self._next_event_id
        self._next_event_id += 1
        self._events.append(event)
        self.num_existing_events += 1
        self._count_event_add(event)
        log_event_history(self.settings, self._config, table_events, event, "NEW")

    def archive_event(self, table_events, event):
        self._perfcounters.count("events")
        event["id"] = self._next_event_id
        self._next_event_id += 1
        event["phase"] = "closed"
        log_event_history(self.settings, self._config, table_events, event, "ARCHIVED")

    def remove_event(self, event):
        try:
            self._events.remove(event)
            self._count_event_remove(event)
        except ValueError:
            self._logger.exception("Cannot remove event %d: not present" % event["id"])

    # protected by lock_eventstatus
    def _remove_event_by_nr(self, index):
        event = self._events.pop(index)
        self._count_event_remove(event)

    # protected by lock_eventstatus
    def remove_oldest_event(self, ty, event):
        if ty == "overall":
            self._logger.verbose("  Removing oldest event")
            self._remove_event_by_nr(0)
        elif ty == "by_rule":
            self._logger.verbose("  Removing oldest event of rule \"%s\"" % event["rule_id"])
            self._remove_oldest_event_of_rule(event["rule_id"])
        elif ty == "by_host":
            self._logger.verbose("  Removing oldest event of host \"%s\"" % event["host"])
            self._remove_oldest_event_of_host(event["host"])

    # protected by lock_eventstatus
    def _remove_oldest_event_of_rule(self, rule_id):
        for event in self._events:
            if event["rule_id"] == rule_id:
                self.remove_event(event)
                return

    # protected by lock_eventstatus
    def _remove_oldest_event_of_host(self, hostname):
        for event in self._events:
            if event["host"] == hostname:
                self.remove_event(event)
                return

    # protected by lock_eventstatus
    def get_num_existing_events_by(self, ty, event):
        if ty == "overall":
            return self.num_existing_events
        elif ty == "by_rule":
            return self.num_existing_events_by_rule.get(event["rule_id"], 0)
        elif ty == "by_host":
            return self.num_existing_events_by_host.get(event["host"], 0)
        else:
            raise NotImplementedError()

    # Cancel all events the belong to a certain rule id and are
    # of the same "breed" as a new event.
    def cancel_events(self, event_server, table_events, new_event, match_groups, rule):
        with lock_eventstatus:
            to_delete = []
            for nr, event in enumerate(self._events):
                if event["rule_id"] == rule["id"]:
                    if self.cancelling_match(match_groups, new_event, event, rule):
                        # Fill a few fields of the cancelled event with data from
                        # the cancelling event so that action scripts have useful
                        # values and the logfile entry if more relevant.
                        previous_phase = event["phase"]
                        event["phase"] = "closed"
                        # TODO: Why do we use OK below and not new_event["state"]???
                        event["state"] = 0  # OK
                        event["text"] = new_event["text"]
                        # TODO: This is a hack and partial copy-n-paste from rewrite_events...
                        if "set_text" in rule:
                            event["text"] = replace_groups(rule["set_text"], event["text"], match_groups)
                        event["time"] = new_event["time"]
                        event["last"] = new_event["time"]
                        event["priority"] = new_event["priority"]
                        log_event_history(self.settings, self._config, table_events, event, "CANCELLED")
                        actions = rule.get("cancel_actions", [])
                        if actions:
                            if previous_phase != "open" \
                               and rule.get("cancel_action_phases", "always") == "open":
                                self._logger.info("Do not execute cancelling actions, event %s's phase "
                                                 "is not 'open' but '%s'" %
                                                 (event["id"], previous_phase))
                            else:
                                do_event_actions(self.settings, self._config, event_server, table_events, actions, event, is_cancelling=True)

                        to_delete.append(nr)

            for nr in to_delete[::-1]:
                self._remove_event_by_nr(nr)

    def cancelling_match(self, match_groups, new_event, event, rule):
        debug = self._config["debug_rules"]

        # The match_groups of the canceling match only contain the *_ok match groups
        # Since the rewrite definitions are based on the positive match, we need to
        # create some missing keys. O.o
        for key in match_groups.keys():
            if key.endswith("_ok"):
                match_groups[key[:-3]] = match_groups[key]

        # Note: before we compare host and application we need to
        # apply the rewrite rules to the event. Because if in the previous
        # the hostname was rewritten, it wouldn't match anymore here.
        host = new_event["host"]
        if "set_host" in rule:
            host = replace_groups(rule["set_host"], host, match_groups)

        if event["host"] != host:
            if debug:
                self._logger.info("Do not cancel event %d: host is not the same (%s != %s)" %
                                 (event["id"], event["host"], host))
            return False

        # The same for the application. But in case there is cancelling based on the application
        # configured in the rule, then don't check for different applications.
        if "cancel_application" not in rule:
            application = new_event["application"]
            if "set_application" in rule:
                application = replace_groups(rule["set_application"], application, match_groups)
            if event["application"] != application:
                if debug:
                    self._logger.info("Do not cancel event %d: application is not the same (%s != %s)" %
                                     (event["id"], event["application"], application))
                return False

        if event["facility"] != new_event["facility"]:
            if debug:
                self._logger.info("Do not cancel event %d: syslog facility is not the same (%d != %d)" %
                                 (event["id"], event["facility"], new_event["facility"]))

        # Make sure, that the matching groups are the same. If the OK match
        # has less groups, we do not care. If it has more groups, then we
        # do not care either. We just compare the common "prefix".
        for nr, (prev_group, cur_group) in enumerate(zip(event["match_groups"],
                                                         match_groups.get("match_groups_message_ok", ()))):
            if prev_group != cur_group:
                if debug:
                    self._logger.info("Do not cancel event %d: match group number "
                                     "%d does not match (%s != %s)" %
                                     (event["id"], nr + 1, prev_group, cur_group))
                return False

        # Note: Duplicated code right above
        # Make sure, that the syslog_application matching groups are the same. If the OK match
        # has less groups, we do not care. If it has more groups, then we
        # do not care either. We just compare the common "prefix".
        for nr, (prev_group, cur_group) in enumerate(zip(event.get("match_groups_syslog_application", ()),
                                                         match_groups.get("match_groups_syslog_application_ok", ()))):
            if prev_group != cur_group:
                if debug:
                    self._logger.info("Do not cancel event %d: syslog application match group number "
                                     "%d does not match (%s != %s)" %
                                     (event["id"], nr + 1, prev_group, cur_group))
                return False

        return True

    def count_rule_match(self, rule_id):
        with lock_eventstatus:
            self._rule_stats.setdefault(rule_id, 0)
            self._rule_stats[rule_id] += 1

    def count_event_up(self, found, event):
        # Update event with new information from new occurrance,
        # but preserve certain attributes from the original (first)
        # event.
        preserve = {
            "count": found.get("count", 1) + 1,
            "first": found["first"],
        }
        # When event is already active then do not change
        # comment or contact information anymore
        if found["phase"] == "open":
            if "comment" in found:
                preserve["comment"] = found["comment"]
            if "contact" in found:
                preserve["contact"] = found["contact"]
        found.update(event)
        found.update(preserve)

    def count_expected_event(self, event_server, table_events, event):
        for ev in self._events:
            if ev["rule_id"] == event["rule_id"] and ev["phase"] == "counting":
                self.count_event_up(ev, event)
                return

        # None found, create one
        event["count"] = 1
        event["phase"] = "counting"
        event_server.new_event_respecting_limits(event)

    def count_event(self, event_server, table_events, event, rule, count):
        # Find previous occurrance of this event and acount for
        # one new occurrance. In case of negated count (expecting rules)
        # we do never modify events that are already in the state "open"
        # since the event has been created because the count was too
        # low in the specified period of time.
        for ev in self._events:
            if ev["rule_id"] == event["rule_id"]:
                if ev["phase"] == "ack" and not count["count_ack"]:
                    continue  # skip acknowledged events

                if count["separate_host"] and ev["host"] != event["host"]:
                    continue  # treat events with separated hosts separately

                if count["separate_application"] and ev["application"] != event["application"]:
                    continue  # same for application

                if count["separate_match_groups"] and ev["match_groups"] != event["match_groups"]:
                    continue

                if count.get("count_duration") is not None and ev["first"] + count["count_duration"] < event["time"]:
                    # Counting has been discontinued on this event after a certain time
                    continue

                if ev["host_in_downtime"] != event["host_in_downtime"]:
                    continue  # treat events with different downtime states separately

                found = ev
                self.count_event_up(found, event)
                break
        else:
            event["count"] = 1
            event["phase"] = "counting"
            event_server.new_event_respecting_limits(event)
            found = event

        # Did we just count the event that was just one too much?
        if found["phase"] == "counting" and found["count"] >= count["count"]:
            found["phase"] = "open"
            return found  # do event action, return found copy of event
        else:
            return False  # do not do event action

    # locked with lock_eventstatus
    def delete_event(self, table_events, event_id, user):
        for nr, event in enumerate(self._events):
            if event["id"] == event_id:
                event["phase"] = "closed"
                if user:
                    event["owner"] = user
                log_event_history(self.settings, self._config, table_events, event, "DELETE", user)
                self._remove_event_by_nr(nr)
                return
        raise MKClientError("No event with id %s" % event_id)

    def get_events(self):
        return self._events

    def get_rule_stats(self):
        return sorted(self._rule_stats.iteritems(), key=lambda x: x[0])


#.
#   .--Actions-------------------------------------------------------------.
#   |                     _        _   _                                   |
#   |                    / \   ___| |_(_) ___  _ __  ___                   |
#   |                   / _ \ / __| __| |/ _ \| '_ \/ __|                  |
#   |                  / ___ \ (__| |_| | (_) | | | \__ \                  |
#   |                 /_/   \_\___|\__|_|\___/|_| |_|___/                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Global functions for executing rule actions like sending emails and  |
#   | executing scripts.                                                   |
#   '----------------------------------------------------------------------'

def event_has_opened(settings, config, event_server, table_events, rule, event):
    # Prepare for events with a limited livetime. This time starts
    # when the event enters the open state or acked state
    if "livetime" in rule:
        livetime, phases = rule["livetime"]
        event["live_until"] = time.time() + livetime
        event["live_until_phases"] = phases

    if rule.get("actions_in_downtime", True) is False and event["host_in_downtime"]:
        logger.info("Skip actions for event %d: Host is in downtime" % event["id"])
        return

    do_event_actions(settings, config, event_server, table_events, rule.get("actions", []), event, is_cancelling=False)


# Execute a list of actions on an event that has just been
# opened or cancelled.
def do_event_actions(settings, config, event_server, table_events, actions, event, is_cancelling):
    for aname in actions:
        if aname == "@NOTIFY":
            do_notify(event_server, event, is_cancelling=is_cancelling)
        else:
            action = config["action"].get(aname)
            if not action:
                logger.info("Cannot execute undefined action '%s'" % aname)
                logger.info("We have to following actions: %s" %
                            ", ".join(config["action"].keys()))
            else:
                logger.info("Going to execute action '%s' on event %d" %
                            (action["title"], event["id"]))
                do_event_action(settings, config, table_events, action, event)


# Rule actions are currently done synchronously. Actions should
# not hang for more than a couple of ms.

def get_quoted_event(event):
    new_event = {}
    fields_to_quote = ["application", "match_groups", "text", "comment", "contact"]
    for key, value in event.iteritems():
        if key not in fields_to_quote:
            new_event[key] = value
        else:
            try:
                if type(value) in [list, tuple]:
                    new_value = map(quote_shell_string, value)
                    if type(value) == tuple:
                        new_value = tuple(value)
                else:
                    new_value = quote_shell_string(value)
                new_event[key] = new_value
            except Exception as e:
                # If anything unforeseen happens, we use the intial value
                new_event[key] = value
                logger.exception("Unable to quote event text %r: %r, %r" % (key, value, e))

    return new_event


def escape_null_bytes(s):
    return s.replace("\000", "\\000")


def do_event_action(settings, config, table_events, action, event, user=""):
    if action["disabled"]:
        logger.info("Skipping disabled action %s." % action["id"])
        return

    try:
        action_type, action_settings = action["action"]
        if action_type == 'email':
            to = escape_null_bytes(substitute_event_tags(table_events, action_settings["to"], event))
            subject = escape_null_bytes(substitute_event_tags(table_events, action_settings["subject"], event))
            body = escape_null_bytes(substitute_event_tags(table_events, action_settings["body"], event))

            send_email(config, to, subject, body)
            log_event_history(settings, config, table_events, event, "EMAIL", user, "%s|%s" % (to, subject))
        elif action_type == 'script':
            execute_script(table_events, escape_null_bytes(substitute_event_tags(table_events, action_settings["script"], get_quoted_event(event))), event)
            log_event_history(settings, config, table_events, event, "SCRIPT", user, action['id'])
        else:
            logger.error("Cannot execute action %s: invalid action type %s" % (action["id"], action_type))
    except Exception:
        if settings.options.debug:
            raise
        logger.exception("Error during execution of action %s" % action["id"])


def get_event_tags(table_events, event):
    substs = [("match_group_%d" % (nr + 1), g)
              for (nr, g)
              in enumerate(event.get("match_groups", ()))]

    for key, defaultvalue in table_events.columns:
        varname = key[6:]
        substs.append((varname, event.get(varname, defaultvalue)))

    def to_string(v):
        if type(v) in [str, unicode]:
            return v
        else:
            return "%s" % v

    tags = {}
    for key, value in substs:
        if type(value) == tuple:
            value = " ".join(map(to_string, value))
        else:
            value = to_string(value)

        tags[key] = value

    return tags


def substitute_event_tags(table_events, text, event):
    for key, value in get_event_tags(table_events, event).iteritems():
        text = text.replace('$%s$' % key.upper(), value)
    return text


def quote_shell_string(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def send_email(config, to, subject, body):
    command_utf8 = ["mail", "-S", "sendcharsets=utf-8",
                    "-s", subject.encode("utf-8"),
                    to.encode("utf-8")]

    if config["debug_rules"]:
        logger.info("  Executing: %s" % " ".join(command_utf8))

    p = subprocess.Popen(command_utf8, close_fds=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    # FIXME: This may lock on too large buffer. We should move all "mail sending" code
    # to a general place and fix this for all our components (notification plugins,
    # notify.py, this one, ...)
    stdout_txt, stderr_txt = p.communicate(body.encode("utf-8"))
    exitcode = p.returncode

    logger.info('  Exitcode: %d' % exitcode)
    if exitcode != 0:
        logger.info("  Error: Failed to send the mail.")
        for line in (stdout_txt + stderr_txt).splitlines():
            logger.info("  Output: %s" % line.rstrip())
        return False

    return True


def execute_script(table_events, body, event):
    script_env = os.environ.copy()

    for key, value in get_event_tags(table_events, event).iteritems():
        if type(key) == unicode:
            key = key.encode("utf-8")
        if type(value) == unicode:
            value = value.encode("utf-8")
        script_env["CMK_" + key.upper()] = value

    # Traps can contain 0-Bytes. We need to remove this from the script
    # body. Otherwise suprocess.Popen will crash.
    p = subprocess.Popen(
        ['/bin/bash'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        close_fds=True,
        env=script_env,
    )
    output = p.communicate(body.encode('utf-8'))[0]
    logger.info('  Exit code: %d' % p.returncode)
    if output:
        logger.info('  Output: \'%s\'' % output)


#.
#   .--Notification--------------------------------------------------------.
#   |         _   _       _   _  __ _           _   _                      |
#   |        | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __           |
#   |        |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \          |
#   |        | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | |         |
#   |        |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  EC create Check_MK native notifications via cmk --notify.           |
#   '----------------------------------------------------------------------'


# Es fehlt:
# - Wenn CONTACTS fehlen, dann müssen in notify.py die Fallbackadressen
#   genommen werden.
# - Was ist mit Nagios als Core. Sendet der CONTACTS? Nein!!
#
# - Das muss sich in den Hilfetexten wiederspiegeln

# This function creates a Check_MK Notification for a locally running Check_MK.
# We simulate a *service* notification.
def do_notify(event_server, event, username=None, is_cancelling=False):
    if core_has_notifications_disabled(event):
        return

    context = create_notification_context(event_server, event, username, is_cancelling)

    if logger.is_verbose():
        logger.verbose("Sending notification via Check_MK with the following context:")
        for varname, value in sorted(context.iteritems()):
            logger.verbose("  %-25s: %s" % (varname, value))

    if context["HOSTDOWNTIME"] != "0":
        logger.info("Host %s is currently in scheduled downtime. "
                    "Skipping notification of event %s." %
                    (context["HOSTNAME"], event["id"]))
        return

    # Send notification context via stdin.
    context_string = to_utf8("".join([
        "%s=%s\n" % (varname, value.replace("\n", "\\n"))
        for (varname, value) in context.iteritems()]))

    p = subprocess.Popen(["cmk", "--notify", "stdin"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         close_fds=True)
    response = p.communicate(input=context_string)[0]
    status = p.returncode
    if status:
        logger.error("Error notifying via Check_MK: %s" % response.strip())
    else:
        logger.info("Successfully forwarded notification for event %d to Check_MK" % event["id"])


def create_notification_context(event_server, event, username, is_cancelling):
    context = base_notification_context(event, username, is_cancelling)
    add_infos_from_monitoring_host(event_server, context, event)  # involves Livestatus query
    add_contacts_from_rule(context, event)
    return context


def add_contacts_from_rule(context, event):
    # Add contact information from the rule, but only if the
    # host is unknown or if contact groups in rule have precedence

    if event.get("contact_groups") is not None and \
       event.get("contact_groups_notify") and (
           "CONTACTS" not in context or
           event.get("contact_groups_precedence", "host") != "host" or
           not event['core_host']):
        add_contact_information_to_context(context, event["contact_groups"])

    # "CONTACTS" is allowed to be missing in the context, cmk --notify will
    # add the fallback contacts then.


def add_infos_from_monitoring_host(event_server, context, event):
    def _add_artificial_context_info():
        context.update({
            "HOSTNAME": event["host"],
            "HOSTALIAS": event["host"],
            "HOSTADDRESS": event["ipaddress"],
            "HOSTTAGS": "",
            "HOSTDOWNTIME": "0",  # Non existing host cannot be in scheduled downtime ;-)
            "CONTACTS": "?",  # Will trigger using fallback contacts
            "SERVICECONTACTGROUPNAMES": "",
        })

    if not event["core_host"]:
        # Host not known in active monitoring. Create artificial host context
        # as good as possible.
        _add_artificial_context_info()
        return

    host_config = event_server.host_config.get(event["core_host"])
    if not host_config:
        _add_artificial_context_info()  # No config found - Host has vanished?
        return

    context.update({
        "HOSTNAME": host_config["name"],
        "HOSTALIAS": host_config["alias"],
        "HOSTADDRESS": host_config["address"],
        "HOSTTAGS": host_config["custom_variables"].get("TAGS", ""),
        "CONTACTS": ",".join(host_config["contacts"]),
        "SERVICECONTACTGROUPNAMES": ",".join(host_config["contact_groups"]),
    })

    # Add custom variables to the notification context
    for key, val in host_config["custom_variables"].iteritems():
        context["HOST_%s" % key] = val

    context["HOSTDOWNTIME"] = "1" if event["host_in_downtime"] else "0"


def base_notification_context(event, username, is_cancelling):
    return {
        "WHAT": "SERVICE",
        "CONTACTNAME": "check-mk-notify",
        "DATE": str(int(event["last"])),  # -> Event: Time
        "MICROTIME": str(int(event["last"] * 1000000)),
        "LASTSERVICESTATE": is_cancelling and "CRITICAL" or "OK",  # better assume OK, we have no transition information
        "LASTSERVICESTATEID": is_cancelling and "2" or "0",  # -> immer OK
        "LASTSERVICEOK": "0",  # 1.1.1970
        "LASTSERVICESTATECHANGE": str(int(event["last"])),
        "LONGSERVICEOUTPUT": "",
        "NOTIFICATIONAUTHOR": username or "",
        "NOTIFICATIONAUTHORALIAS": username or "",
        "NOTIFICATIONAUTHORNAME": username or "",
        "NOTIFICATIONCOMMENT": "",
        "NOTIFICATIONTYPE": is_cancelling and "RECOVERY" or "PROBLEM",
        "SERVICEACKAUTHOR": "",
        "SERVICEACKCOMMENT": "",
        "SERVICEATTEMPT": "1",
        "SERVICECHECKCOMMAND": event["rule_id"] is None and "ec-internal" or "ec-rule-" + event["rule_id"],
        "SERVICEDESC": event["application"] or "Event Console",
        "SERVICENOTIFICATIONNUMBER": "1",
        "SERVICEOUTPUT": event["text"],
        "SERVICEPERFDATA": "",
        "SERVICEPROBLEMID": "ec-id-" + str(event["id"]),
        "SERVICESTATE": defines.service_state_name(event["state"]),
        "SERVICESTATEID": str(event["state"]),
        "SERVICE_EC_CONTACT": event.get("owner", ""),
        "SERVICE_SL": str(event["sl"]),
        "SVC_SL": str(event["sl"]),

        # Some fields only found in EC notifications
        "EC_ID": str(event["id"]),
        "EC_RULE_ID": event["rule_id"] or "",
        "EC_PRIORITY": str(event["priority"]),
        "EC_FACILITY": str(event["facility"]),
        "EC_PHASE": event["phase"],
        "EC_COMMENT": event.get("comment", ""),
        "EC_OWNER": event.get("owner", ""),
        "EC_CONTACT": event.get("contact", ""),
        "EC_PID": str(event.get("pid", 0)),
        "EC_MATCH_GROUPS": "\t".join(event["match_groups"]),
        "EC_CONTACT_GROUPS": " ".join(event.get("contact_groups") or []),
        "EC_ORIG_HOST": event.get("orig_host", event["host"]),
    }


def add_contact_information_to_context(context, contact_groups):
    contact_names = rbn_groups_contacts(contact_groups)
    context["CONTACTS"] = ",".join(contact_names)
    context["SERVICECONTACTGROUPNAMES"] = ",".join(contact_groups)
    logger.verbose("Setting %d contacts %s resulting from rule contact groups %s" %
                   (len(contact_names), ",".join(contact_names), ",".join(contact_groups)))


# NOTE: This function is an exact copy from modules/notify.py. We need
# to move all this Check_MK-specific livestatus query stuff to a helper
# module in lib some day.
def rbn_groups_contacts(groups):
    if not groups:
        return {}
    query = "GET contactgroups\nColumns: members\n"
    for group in groups:
        query += "Filter: name = %s\n" % group
    query += "Or: %d\n" % len(groups)

    try:
        contacts = set([])
        for contact_list in livestatus.LocalConnection().query_column(query):
            contacts.update(contact_list)
        return contacts

    except livestatus.MKLivestatusNotFoundError:
        return []

    except Exception:
        if cmk.debug.enabled():
            raise
        return []


def core_has_notifications_disabled(event):
    try:
        notifications_enabled = livestatus.LocalConnection().query_value("GET status\nColumns: enable_notifications")
        if not notifications_enabled:
            logger.info("Notifications are currently disabled. Skipped notification for event %d" % event["id"])
            return True
    except Exception as e:
        logger.info("Cannot determine whether notifcations are enabled in core: %s. Assuming YES." % e)

    return False


#.
#   .--Replication---------------------------------------------------------.
#   |           ____            _ _           _   _                        |
#   |          |  _ \ ___ _ __ | (_) ___ __ _| |_(_) ___  _ __             |
#   |          | |_) / _ \ '_ \| | |/ __/ _` | __| |/ _ \| '_ \            |
#   |          |  _ <  __/ |_) | | | (_| (_| | |_| | (_) | | | |           |
#   |          |_| \_\___| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|           |
#   |                    |_|                                               |
#   +----------------------------------------------------------------------+
#   |  Functions for doing replication, master and slave parts.            |
#   '----------------------------------------------------------------------'

def is_replication_slave(config):
    repl_settings = config["replication"]
    return repl_settings and not repl_settings.get("disabled")


def replication_allow_command(config, command, slave_status):
    if is_replication_slave(config) and slave_status["mode"] == "sync" \
       and command in ["DELETE", "UPDATE", "CHANGESTATE", "ACTION"]:
        raise MKClientError("This command is not allowed on a replication slave "
                            "while it is in sync mode.")


def replication_send(config, event_status, last_update):
    response = {}
    with lock_configuration:
        response["status"] = event_status.pack_status()
        if last_update < config["last_reload"]:
            response["rules"] = config["rules"]  # Remove one bright day, where legacy rules are not needed anymore
            response["rule_packs"] = config["rule_packs"]
            response["actions"] = config["actions"]
        return response


def replication_pull(settings, config, perfcounters, event_status, event_server, slave_status):
    # We distinguish two modes:
    # 1. slave mode: just pull the current state from the master.
    #    if the master is not reachable then decide whether to
    #    switch to takeover mode.
    # 2. takeover mode: if automatic fallback is enabled and the
    #    time frame for that has not yet ellapsed, then try to
    #    pull the current state from the master. If that is successful
    #    then switch back to slave mode. If not automatic fallback
    #    is enabled then simply do nothing.
    now = time.time()
    repl_settings = config["replication"]
    mode = slave_status["mode"]
    need_sync = mode == "sync" or (mode == "takeover" and "fallback" in repl_settings and
                                   (slave_status["last_master_down"] is None or
                                    now - repl_settings["fallback"] < slave_status["last_master_down"]))

    if need_sync:
        with lock_eventstatus:
            with lock_configuration:

                try:
                    new_state = get_state_from_master(config, slave_status)
                    replication_update_state(settings, config, event_status, event_server, new_state)
                    if repl_settings.get("logging"):
                        logger.info("Successfully synchronized with master")
                    slave_status["last_sync"] = now
                    slave_status["success"] = True

                    # Fall back to slave mode after successful sync
                    # (time frame has already been checked)
                    if mode == "takeover":
                        if slave_status["last_master_down"] is None:
                            logger.info("Replication: master reachable for the first time, "
                                        "switching back to slave mode")
                            slave_status["mode"] = "sync"
                        else:
                            logger.info("Replication: master reachable again after %d seconds, "
                                        "switching back to sync mode" % (now - slave_status["last_master_down"]))
                            slave_status["mode"] = "sync"
                    slave_status["last_master_down"] = None

                except Exception as e:
                    logger.warning("Replication: cannot sync with master: %s" % e)
                    slave_status["success"] = False
                    if slave_status["last_master_down"] is None:
                        slave_status["last_master_down"] = now

                    # Takeover
                    if "takeover" in repl_settings and mode != "takeover":
                        if not slave_status["last_sync"]:
                            if repl_settings.get("logging"):
                                logger.error("Replication: no takeover since master was never reached.")
                        else:
                            offline = now - slave_status["last_sync"]
                            if offline < repl_settings["takeover"]:
                                if repl_settings.get("logging"):
                                    logger.warning("Replication: no takeover yet, still %d seconds to wait" %
                                                   (repl_settings["takeover"] - offline))
                            else:
                                logger.info("Replication: master not reached for %d seconds, taking over!" %
                                            offline)
                                slave_status["mode"] = "takeover"

                save_slave_status(settings, slave_status)

                # Compute statistics of the average time needed for a sync
                perfcounters.count_time("sync", time.time() - now)


def replication_update_state(settings, config, event_status, event_server, new_state):

    # Keep a copy of the masters' rules and actions and also prepare using them
    if "rules" in new_state:
        save_master_config(settings, new_state)
        event_server.compile_rules(new_state["rules"], new_state.get("rule_packs", []))
        config["actions"] = new_state["actions"]

    # Update to the masters' event state
    event_status.unpack_status(new_state["status"])


def save_master_config(settings, new_state):
    path = settings.paths.master_config_file.value
    path_new = path.parent / (path.name + '.new')
    path_new.write_bytes(repr({
        "rules": new_state["rules"],
        "rule_packs": new_state["rule_packs"],
        "actions": new_state["actions"],
        }) + "\n")
    path_new.rename(path)


def load_master_config(settings, config):
    path = settings.paths.master_config_file.value
    try:
        config = ast.literal_eval(path.read_bytes())
        config["rules"] = config["rules"]
        config["rule_packs"] = config.get("rule_packs", [])
        config["actions"] = config["actions"]
        logger.info("Replication: restored %d rule packs and %d actions from %s" %
                    (len(config["rule_packs"]), len(config["actions"]), path))
    except Exception:
        if is_replication_slave(config):
            logger.error("Replication: no previously saved master state available")


def get_state_from_master(config, slave_status):
    repl_settings = config["replication"]
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(repl_settings["connect_timeout"])
        sock.connect(repl_settings["master"])
        sock.sendall("REPLICATE %d\n" %
                     (slave_status["last_sync"] and slave_status["last_sync"] or 0))
        sock.shutdown(socket.SHUT_WR)

        response_text = ""
        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return ast.literal_eval(response_text)
    except SyntaxError as e:
        raise Exception("Invalid response from event daemon: <pre>%s</pre>" % response_text)

    except IOError as e:
        raise Exception("Master not responding: %s" % e)

    except Exception as e:
        raise Exception("Cannot connect to event daemon: %s" % e)


def save_slave_status(settings, slave_status):
    settings.paths.slave_status_file.value.write_bytes(repr(slave_status) + "\n")


def default_slave_status_master():
    return {
        "last_sync": 0,
        "last_master_down": None,
        "mode": "master",
        "average_sync_time": None,
    }


def default_slave_status_sync():
    return {
        "last_sync": 0,
        "last_master_down": None,
        "mode": "sync",
        "average_sync_time": None,
    }


def update_slave_status(slave_status, settings, config):
    path = settings.paths.slave_status_file.value
    if is_replication_slave(config):
        try:
            slave_status.update(ast.literal_eval(path.read_bytes()))
        except Exception:
            slave_status.update(default_slave_status_sync())
            save_slave_status(settings, slave_status)
    else:
        if path.exists():
            path.unlink()
        slave_status.update(default_slave_status_master())


#.
#   .--Configuration-------------------------------------------------------.
#   |    ____             __ _                       _   _                 |
#   |   / ___|___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __      |
#   |  | |   / _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \     |
#   |  | |__| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |    |
#   |   \____\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|    |
#   |                          |___/                                       |
#   +----------------------------------------------------------------------+
#   |  Loading of the configuration files                                  |
#   '----------------------------------------------------------------------'

def load_configuration(settings, slave_status):
    config = cmk.ec.export.load_config(settings)

    # If not set by command line, set the log level by configuration
    if settings.options.verbosity == 0:
        levels = config["log_level"]
        logger.setLevel(levels["cmk.mkeventd"])
        logger.getChild("EventServer").setLevel(levels["cmk.mkeventd.EventServer"])
        if "cmk.mkeventd.EventServer.snmp" in levels:
            logger.getChild("EventServer.snmp").setLevel(levels["cmk.mkeventd.EventServer.snmp"])
        logger.getChild("EventStatus").setLevel(levels["cmk.mkeventd.EventStatus"])
        logger.getChild("StatusServer").setLevel(levels["cmk.mkeventd.StatusServer"])
        logger.getChild("lock").setLevel(levels["cmk.mkeventd.lock"])

    # Configure the auto deleting indexes in the DB when mongodb is enabled
    if config['archive_mode'] == 'mongodb':
        update_mongodb_indexes(settings)
        update_mongodb_history_lifetime(settings, config)

    # Are we a replication slave? Parts of the configuration
    # will be overridden by values from the master.
    update_slave_status(slave_status, settings, config)
    if is_replication_slave(config):
        logger.info("Replication: slave configuration, current mode: %s" %
                    slave_status["mode"])
    load_master_config(settings, config)

    # Create dictionary for actions for easy access
    config["action"] = {}
    for action in config["actions"]:
        config["action"][action["id"]] = action

    config["last_reload"] = time.time()

    return config


def reload_configuration(settings, event_status, event_server, status_server, slave_status):
    with lock_configuration:
        config = load_configuration(settings, slave_status)
        initialize_snmptrap_handling(settings, config, event_server, status_server.table_events)
        event_server.reload_configuration(config)

    event_status.reload_configuration(config)
    status_server.reload_configuration(config)
    logger.info("Reloaded configuration.")


def snmptrap_translation_enabled(config):
    return config["translate_snmptraps"] is not False


#.
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Main entry and option parsing                                       |
#   '----------------------------------------------------------------------'

# Create locks for global data structures
lock_eventstatus = ECLock("eventstatus")
lock_configuration = ECLock("configuration")
lock_logging = ECLock("history")


def main():
    os.unsetenv("LANG")

    settings = cmk.ec.settings.settings(cmk.__version__,
                                        pathlib.Path(cmk.paths.omd_root),
                                        pathlib.Path(cmk.paths.default_config_dir),
                                        sys.argv)

    pid_path = None
    try:
        cmk.log.open_log(sys.stderr)
        cmk.log.set_verbosity(settings.options.verbosity)

        settings.paths.log_file.value.parent.mkdir(parents=True, exist_ok=True)
        if not settings.options.foreground:
            cmk.log.open_log(str(settings.paths.log_file.value))

        logger.info("-" * 65)
        logger.info("mkeventd version %s starting" % cmk.__version__)

        slave_status = default_slave_status_master()
        config = load_configuration(settings, slave_status)

        pid_path = settings.paths.pid_file.value
        if pid_path.exists():
            old_pid = int(pid_path.read_text(encoding='utf-8'))
            if process_exists(old_pid):
                bail_out("Old PID file %s still existing and mkeventd still running with PID %d." % (pid_path, old_pid))
            pid_path.unlink()
            logger.info("Removed orphaned PID file %s (process %d not running anymore)." % (pid_path, old_pid))

        # Make sure paths exist
        settings.paths.event_pipe.value.parent.mkdir(parents=True, exist_ok=True)
        settings.paths.status_file.value.parent.mkdir(parents=True, exist_ok=True)

        # First do all things that might fail, before daemonizing
        perfcounters = Perfcounters()
        event_status = EventStatus(settings, config, perfcounters)
        table_events = StatusTableEvents(event_status)
        event_server = EventServer(settings, config, slave_status, perfcounters, event_status, table_events)
        terminate_main_event = threading.Event()
        status_server = StatusServer(settings, config, slave_status, perfcounters, event_status, event_server, table_events, terminate_main_event)

        event_status.load_status(event_server)

        initialize_snmptrap_handling(settings, config, event_server, table_events)

        event_server.compile_rules(config["rules"], config["rule_packs"])

        if not settings.options.foreground:
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            cmk.daemon.daemonize()
            logger.info("Daemonized with PID %d." % os.getpid())

        cmk.daemon.lock_with_pid_file(str(pid_path))

        # Install signal hander
        signal.signal(signal.SIGHUP, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGQUIT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Now let's go...
        run_eventd(terminate_main_event, settings, config, perfcounters, event_status, event_server, status_server, slave_status)

        # We reach this point, if the server has been killed by
        # a signal or hitting Ctrl-C (in foreground mode)

        # TODO: Move this cleanup stuff to the classes that are responsible for these ressources

        # Remove event pipe and drain it, so that we make sure
        # that processes (syslog, etc) will not hang when trying
        # to write into the pipe.
        logger.verbose("Cleaning up event pipe")
        pipe = event_server.open_pipe()  # Open it
        settings.paths.event_pipe.value.unlink() # Remove pipe
        drain_pipe(pipe)                   # Drain any data
        os.close(pipe)                     # Close pipe

        logger.verbose("Saving final event state")
        event_status.save_status()

        logger.verbose("Cleaning up sockets")
        settings.paths.unix_socket.value.unlink()
        settings.paths.event_socket.value.unlink()

        logger.verbose("Output hash stats")
        event_server.output_hash_stats()

        logger.verbose("Closing fds which might be still open")
        for fd in [settings.options.syslog_udp,
                   settings.options.syslog_tcp,
                   settings.options.snmptrap_udp]:
            try:
                if isinstance(fd, cmk.ec.settings.FileDescriptor):
                    os.close(fd.value)
            except Exception:
                pass

        logger.info("Successfully shut down.")
        sys.exit(0)

    except Exception:
        if settings.options.debug:
            raise
        bail_out(traceback.format_exc())

    finally:
        if pid_path and cmk.store.have_lock(str(pid_path)):
            try:
                pid_path.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    main()
