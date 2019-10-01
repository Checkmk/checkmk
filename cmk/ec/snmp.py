#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
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

import traceback

# Needed for receiving traps
import pysnmp.debug
import pysnmp.entity.config
import pysnmp.entity.engine
import pysnmp.entity.rfc3413.ntfrcv
import pysnmp.proto.api
import pysnmp.proto.errind

# Needed for trap translation
import pysnmp.smi.builder
import pysnmp.smi.view
import pysnmp.smi.rfc1902
import pysnmp.smi.error
import pyasn1.error

from cmk.utils.log import VERBOSE
import cmk.utils.render


class SNMPTrapEngine(object):

    # Disable receiving of SNMPv3 INFORM messages. We do not support them (yet)
    class ECNotificationReceiver(pysnmp.entity.rfc3413.ntfrcv.NotificationReceiver):
        pduTypes = (pysnmp.proto.api.v1.TrapPDU.tagSet, pysnmp.proto.api.v2c.SNMPv2TrapPDU.tagSet)

    def __init__(self, settings, config, logger, callback):
        super(SNMPTrapEngine, self).__init__()
        self._logger = logger
        if settings.options.snmptrap_udp is None:
            return
        self.snmp_engine = pysnmp.entity.engine.SnmpEngine()
        self._initialize_snmp_credentials(config)
        self._snmp_receiver = SNMPTrapEngine.ECNotificationReceiver(self.snmp_engine,
                                                                    self._handle_snmptrap)
        self._snmp_trap_translator = SNMPTrapTranslator(settings, config, logger)
        self._callback = callback

        # Hand over our logger to PySNMP
        pysnmp.debug.setLogger(pysnmp.debug.Debug("all", printer=logger.debug))

        self.snmp_engine.observer.registerObserver(self._handle_unauthenticated_snmptrap,
                                                   "rfc2576.prepareDataElements:sm-failure",
                                                   "rfc3412.prepareDataElements:sm-failure")

    @staticmethod
    def _auth_proto_for(proto_name):
        if proto_name == "md5":
            return pysnmp.entity.config.usmHMACMD5AuthProtocol
        if proto_name == "sha":
            return pysnmp.entity.config.usmHMACSHAAuthProtocol
        raise Exception("Invalid SNMP auth protocol: %s" % proto_name)

    @staticmethod
    def _priv_proto_for(proto_name):
        if proto_name == "DES":
            return pysnmp.entity.config.usmDESPrivProtocol
        if proto_name == "AES":
            return pysnmp.entity.config.usmAesCfb128Protocol
        raise Exception("Invalid SNMP priv protocol: %s" % proto_name)

    def _initialize_snmp_credentials(self, config):
        user_num = 0
        for spec in config["snmp_credentials"]:
            credentials = spec["credentials"]
            user_num += 1

            # SNMPv1/v2
            if not isinstance(credentials, tuple):
                community_index = 'snmpv2-%d' % user_num
                self._logger.info("adding SNMPv1 system: communityIndex=%s" % community_index)
                pysnmp.entity.config.addV1System(self.snmp_engine, community_index, credentials)
                continue

            # SNMPv3
            securityLevel = credentials[0]
            if securityLevel == "noAuthNoPriv":
                user_id = credentials[1]
                auth_proto = pysnmp.entity.config.usmNoAuthProtocol
                auth_key = None
                priv_proto = pysnmp.entity.config.usmNoPrivProtocol
                priv_key = None
            elif securityLevel == "authNoPriv":
                user_id = credentials[2]
                auth_proto = self._auth_proto_for(credentials[1])
                auth_key = credentials[3]
                priv_proto = pysnmp.entity.config.usmNoPrivProtocol
                priv_key = None
            elif securityLevel == "authPriv":
                user_id = credentials[2]
                auth_proto = self._auth_proto_for(credentials[1])
                auth_key = credentials[3]
                priv_proto = self._priv_proto_for(credentials[4])
                priv_key = credentials[5]
            else:
                raise Exception("Invalid SNMP security level: %s" % securityLevel)

            for engine_id in spec.get("engine_ids", []):
                self._logger.info(
                    "adding SNMPv3 user: userName=%s, authProtocol=%s, privProtocol=%s, securityEngineId=%s"
                    % (user_id, ".".join(str(i) for i in auth_proto), ".".join(
                        str(i) for i in priv_proto), engine_id))
                pysnmp.entity.config.addV3User(
                    self.snmp_engine,
                    user_id,
                    auth_proto,
                    auth_key,
                    priv_proto,
                    priv_key,
                    securityEngineId=pysnmp.proto.api.v2c.OctetString(hexValue=engine_id))

    def process_snmptrap(self, message, sender_address):
        """Receives an incoming SNMP trap from the socket and hands it over to PySNMP for parsing
        and processing. PySNMP is calling the registered call back (self._handle_snmptrap) back."""
        self._logger.log(VERBOSE, "Trap received from %s:%d. Checking for acceptance now.",
                         sender_address)
        self.snmp_engine.setUserContext(sender_address=sender_address)
        self.snmp_engine.msgAndPduDsp.receiveMessage(snmpEngine=self.snmp_engine,
                                                     transportDomain=(),
                                                     transportAddress=sender_address,
                                                     wholeMsg=message)

    def _handle_snmptrap(self, snmp_engine, state_reference, context_engine_id, context_name,
                         var_binds, cb_ctx):
        ipaddress = self.snmp_engine.getUserContext("sender_address")[0]
        self._log_snmptrap_details(context_engine_id, context_name, var_binds, ipaddress)
        trap = self._snmp_trap_translator.translate(ipaddress, var_binds)
        self._callback(trap, ipaddress)

    def _log_snmptrap_details(self, context_engine_id, context_name, var_binds, ipaddress):
        if self._logger.isEnabledFor(VERBOSE):
            self._logger.log(VERBOSE,
                             'Trap accepted from %s (ContextEngineId "%s", ContextName "%s")',
                             ipaddress, context_engine_id.prettyPrint(), context_name.prettyPrint())

            for name, val in var_binds:
                self._logger.log(VERBOSE, '%-40s = %s', name.prettyPrint(), val.prettyPrint())

    def _handle_unauthenticated_snmptrap(self, snmp_engine, execpoint, variables, cb_ctx):
        if variables["securityLevel"] in [1, 2] and variables["statusInformation"][
                "errorIndication"] == pysnmp.proto.errind.unknownCommunityName:
            msg = "Unknown community (%s)" % variables["statusInformation"].get("communityName", "")
        elif variables["securityLevel"] == 3 and variables["statusInformation"][
                "errorIndication"] == pysnmp.proto.errind.unknownSecurityName:
            msg = "Unknown credentials (msgUserName: %s)" % variables["statusInformation"].get(
                "msgUserName", "")
        else:
            msg = "%s" % variables["statusInformation"]

        self._logger.log(VERBOSE, "Trap (v%d) dropped from %s: %s", variables["securityLevel"],
                         variables["transportAddress"][0], msg)


class SNMPTrapTranslator(object):
    def __init__(self, settings, config, logger):
        super(SNMPTrapTranslator, self).__init__()
        self._logger = logger
        translation_config = config["translate_snmptraps"]
        if translation_config is False:
            self.translate = self._translate_simple
        elif translation_config == (True, {}):
            self._mib_resolver = self._construct_resolver(logger,
                                                          settings.paths.compiled_mibs_dir.value,
                                                          False)
            self.translate = self._translate_via_mibs
        elif translation_config == (True, {'add_description': True}):
            self._mib_resolver = self._construct_resolver(logger,
                                                          settings.paths.compiled_mibs_dir.value,
                                                          True)
            self.translate = self._translate_via_mibs
        else:
            raise Exception("invalid SNMP trap translation")

    @staticmethod
    def _construct_resolver(logger, mibs_dir, load_texts):
        try:
            builder = pysnmp.smi.builder.MibBuilder()  # manages python MIB modules

            # load MIBs from our compiled MIB and default MIB paths
            builder.setMibSources(*[pysnmp.smi.builder.DirMibSource(str(mibs_dir))] +
                                  list(builder.getMibSources()))

            # Indicate if we wish to load DESCRIPTION and other texts from MIBs
            builder.loadTexts = load_texts

            # This loads all or specified pysnmp MIBs into memory
            builder.loadModules()

            loaded_mib_module_names = builder.mibSymbols.keys()
            logger.info('Loaded %d SNMP MIB modules' % len(loaded_mib_module_names))
            logger.log(VERBOSE, 'Found modules: %s', ', '.join(loaded_mib_module_names))

            # This object maintains various indices built from MIBs data
            return pysnmp.smi.view.MibViewController(builder)
        except pysnmp.smi.error.SmiError as e:
            logger.info("Exception while loading MIB modules. Proceeding without modules!")
            logger.exception("Exception: %s" % e)
            return None

    # Convert pysnmp datatypes to simply handable ones
    def _translate_simple(self, ipaddress, var_bind_list):
        var_binds = []
        for oid, value in var_bind_list:
            key = str(oid)

            if value.__class__.__name__ in ['ObjectIdentifier', 'IpAddress']:
                val = value.prettyPrint()
            elif value.__class__.__name__ == 'TimeTicks':
                val = str(cmk.utils.render.Age(float(value._value) / 100))
            else:
                val = value._value

            # Translate some standard SNMPv2 oids
            if key == '1.3.6.1.2.1.1.3.0':
                key = 'Uptime'

            var_binds.append((key, val))
        return var_binds

    # Convert pysnmp datatypes to simply handable ones
    def _translate_via_mibs(self, ipaddress, var_bind_list):
        var_binds = []
        if self._mib_resolver is None:
            self._logger.warning('Failed to translate OIDs, no modules loaded (see above)')
            # TODO: Fall back to _translate_simple?
            return [(str(oid), str(value)) for oid, value in var_bind_list]

        def do_translate(oid, value):
            # Disable mib_var[0] type detection
            # pylint: disable=no-member
            mib_var = pysnmp.smi.rfc1902.ObjectType(pysnmp.smi.rfc1902.ObjectIdentity(oid),
                                                    value).resolveWithMib(self._mib_resolver)

            node = mib_var[0].getMibNode()
            translated_oid = mib_var[0].prettyPrint().replace("\"", "")
            translated_value = mib_var[1].prettyPrint()

            return node, translated_oid, translated_value

        for oid, value in var_bind_list:
            try:
                node, translated_oid, translated_value = do_translate(oid, value)
                units = node.getUnits() if hasattr(node, "getUnits") else ""
                if units:
                    translated_value += ' %s' % units
                description = node.getDescription() if hasattr(node, "getDescription") else ""
                if description:
                    translated_value += "(%s)" % description
            except (pysnmp.smi.error.SmiError, pyasn1.error.ValueConstraintError) as e:
                self._logger.warning('Failed to translate OID %s (in trap from %s): %s '
                                     '(enable debug logging for details)' %
                                     (oid.prettyPrint(), ipaddress, e))
                self._logger.debug('Failed trap var binds:\n%s' %
                                   "\n".join(["%s: %r" % i for i in var_bind_list]))
                self._logger.debug(traceback.format_exc())
                translated_oid = str(oid)
                translated_value = str(value)
            var_binds.append((translated_oid, translated_value))

        return var_binds
