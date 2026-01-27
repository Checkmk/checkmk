#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: We *really* need type stubs or a typed version of the SNMP libraries...
# mypy: disable-error-code="no-untyped-call"

import traceback
from collections.abc import Iterable, Mapping
from logging import Logger
from pathlib import Path
from typing import Any

import pyasn1.error
import pysnmp.debug
import pysnmp.entity.config
import pysnmp.entity.engine
import pysnmp.entity.rfc3413.ntfrcv
import pysnmp.proto.api
import pysnmp.proto.errind
import pysnmp.proto.rfc1155
import pysnmp.proto.rfc1902
import pysnmp.smi.builder
import pysnmp.smi.error
import pysnmp.smi.rfc1902
import pysnmp.smi.view
from pyasn1.type.base import SimpleAsn1Type
from pysmi.codegen.pysnmp import PySnmpCodeGen
from pysmi.compiler import MibCompiler, MibStatus
from pysmi.parser.smiv1compat import SmiV1CompatParser
from pysmi.reader.callback import CallbackReader
from pysmi.reader.localfile import FileReader
from pysmi.searcher.pyfile import PyFileSearcher
from pysmi.searcher.pypackage import PyPackageSearcher
from pysmi.searcher.stub import StubSearcher
from pysmi.writer.pyfile import PyFileWriter

from .config import AuthenticationProtocol, Config, PrivacyProtocol
from .log_level import VERBOSE
from .settings import Paths, Settings

VarBind = tuple[pysnmp.proto.rfc1902.ObjectName, SimpleAsn1Type]
VarBinds = Iterable[VarBind]


class SNMPTrapParser:
    # Disable receiving of SNMPv3 INFORM messages. We do not support them (yet)
    class _ECNotificationReceiver(pysnmp.entity.rfc3413.ntfrcv.NotificationReceiver):
        SUPPORTED_PDU_TYPES = (
            pysnmp.proto.api.v1.TrapPDU.tagSet,
            pysnmp.proto.api.v2c.SNMPv2TrapPDU.tagSet,
        )  # type: ignore[assignment]

    def __init__(self, settings: Settings, config: Config, logger: Logger) -> None:
        self._logger = logger
        if settings.options.snmptrap_udp is None:
            return

        # Hand over our logger to PySNMP
        pysnmp.debug.set_logger(pysnmp.debug.Debug("all", printer=logger.debug))

        self.snmp_engine = pysnmp.entity.engine.SnmpEngine()
        self._initialize_snmp_credentials(config)
        # NOTE: pysnmp has a really strange notification receiver API: The constructor call below
        # effectively registers the callback (2nd argument) at the SNMP engine. The resulting
        # receiver instance is kept alive by the registration itself, so there is no need to store
        # it anywhere here. The callback stores the parsed trap in _varbinds_and_ipaddress when
        # parse() is called.
        SNMPTrapParser._ECNotificationReceiver(
            self.snmp_engine,
            self._handle_snmptrap,
        )
        self._varbinds_and_ipaddress: tuple[Iterable[tuple[str, str]], str] | None = None
        self._snmp_trap_translator = SNMPTrapTranslator(settings, config, logger)

        self.snmp_engine.observer.register_observer(
            self._handle_unauthenticated_snmptrap,
            "rfc2576.prepareDataElements:sm-failure",
            "rfc3412.prepareDataElements:sm-failure",
        )

    @staticmethod
    def _auth_proto_for(proto_name: AuthenticationProtocol) -> tuple[int, ...]:
        if proto_name == "md5":
            return pysnmp.entity.config.USM_AUTH_HMAC96_MD5
        if proto_name == "sha":
            return pysnmp.entity.config.USM_AUTH_HMAC96_SHA
        if proto_name == "SHA-224":
            return pysnmp.entity.config.USM_AUTH_HMAC128_SHA224
        if proto_name == "SHA-256":
            return pysnmp.entity.config.USM_AUTH_HMAC192_SHA256
        if proto_name == "SHA-384":
            return pysnmp.entity.config.USM_AUTH_HMAC256_SHA384
        if proto_name == "SHA-512":
            return pysnmp.entity.config.USM_AUTH_HMAC384_SHA512
        raise Exception(f"Invalid SNMP auth protocol: {proto_name}")

    @staticmethod
    def _priv_proto_for(proto_name: PrivacyProtocol) -> tuple[int, ...]:
        if proto_name == "DES":
            return pysnmp.entity.config.USM_PRIV_CBC56_DES
        if proto_name == "3DES-EDE":
            return pysnmp.entity.config.USM_PRIV_CBC168_3DES
        if proto_name == "AES":
            return pysnmp.entity.config.USM_PRIV_CFB128_AES
        if proto_name == "AES-192":
            return pysnmp.entity.config.USM_PRIV_CFB192_AES
        if proto_name == "AES-256":
            return pysnmp.entity.config.USM_PRIV_CFB256_AES
        if proto_name == "AES-192-Blumenthal":
            return pysnmp.entity.config.USM_PRIV_CFB192_AES_BLUMENTHAL
        if proto_name == "AES-256-Blumenthal":
            return pysnmp.entity.config.USM_PRIV_CFB256_AES_BLUMENTHAL
        raise Exception(f"Invalid SNMP priv protocol: {proto_name}")

    def _initialize_snmp_credentials(self, config: Config) -> None:
        user_num = 0
        for spec in config["snmp_credentials"]:
            credentials = spec["credentials"]
            user_num += 1

            # SNMPv1/v2
            if not isinstance(credentials, tuple):
                community_index = f"snmpv2-{user_num}"
                self._logger.info("adding SNMPv1 system: communityIndex=%s", community_index)
                pysnmp.entity.config.add_v1_system(self.snmp_engine, community_index, credentials)
                continue

            # SNMPv3
            if credentials[0] == "noAuthNoPriv":
                user_id = credentials[1]
                auth_proto: tuple[int, ...] = pysnmp.entity.config.USM_AUTH_NONE
                auth_key = None
                priv_proto: tuple[int, ...] = pysnmp.entity.config.USM_PRIV_NONE
                priv_key = None
            elif credentials[0] == "authNoPriv":
                user_id = credentials[2]
                auth_proto = self._auth_proto_for(credentials[1])
                auth_key = credentials[3]
                priv_proto = pysnmp.entity.config.USM_PRIV_NONE
                priv_key = None
            elif credentials[0] == "authPriv":
                user_id = credentials[2]
                auth_proto = self._auth_proto_for(credentials[1])
                auth_key = credentials[3]
                priv_proto = self._priv_proto_for(credentials[4])
                priv_key = credentials[5]
            else:
                raise Exception(f"Invalid SNMP security level: {credentials[0]}")

            for engine_id in spec.get("engine_ids", []):
                self._logger.info(
                    "adding SNMPv3 user: userName=%s, authProtocol=%s, privProtocol=%s, securityEngineId=%s",
                    user_id,
                    ".".join(str(i) for i in auth_proto),
                    ".".join(str(i) for i in priv_proto),
                    engine_id,
                )
                pysnmp.entity.config.add_v3_user(
                    self.snmp_engine,
                    user_id,
                    auth_proto,
                    auth_key,
                    priv_proto,
                    priv_key,
                    securityEngineId=pysnmp.proto.api.v2c.OctetString(hexValue=engine_id),
                )

    def parse(
        self, data: bytes, sender_address: tuple[str, int]
    ) -> tuple[Iterable[tuple[str, str]], str] | None:
        """Let PySNMP parse the given trap data. The _handle_snmptrap() callback below collects the result."""
        self._logger.log(
            VERBOSE, "Trap received from %s:%d. Checking for acceptance now.", sender_address
        )
        self._varbinds_and_ipaddress = None
        self.snmp_engine.set_user_context(sender_address=sender_address)
        self.snmp_engine.message_dispatcher.receive_message(
            snmpEngine=self.snmp_engine,
            transportDomain=(),
            transportAddress=sender_address,
            wholeMsg=data,
        )
        return self._varbinds_and_ipaddress

    def _handle_snmptrap(
        self,
        snmp_engine: pysnmp.entity.engine.SnmpEngine,
        state_reference: str,
        context_engine_id: pysnmp.smi.rfc1902.ObjectIdentity,
        context_name: pysnmp.proto.rfc1902.ObjectName,
        var_binds: VarBinds,
        cb_ctx: None,
    ) -> None:
        # sender_address contains a (host: str, port: int) tuple
        ipaddress: str = self.snmp_engine.get_user_context("sender_address")[0]  # type: ignore[index]
        self._log_snmptrap_details(context_engine_id, context_name, var_binds, ipaddress)
        trap = self._snmp_trap_translator.translate(ipaddress, var_binds)
        # NOTE: There can be only one trap per PDU, so we don't run into the risk of overwriting previous info.
        self._varbinds_and_ipaddress = trap, ipaddress

    def _log_snmptrap_details(
        self,
        context_engine_id: pysnmp.smi.rfc1902.ObjectIdentity,
        context_name: pysnmp.proto.rfc1902.ObjectName,
        var_binds: VarBinds,
        ipaddress: str,
    ) -> None:
        if self._logger.isEnabledFor(VERBOSE):
            self._logger.log(
                VERBOSE,
                'Trap accepted from %s (ContextEngineId "%s", SNMPContext "%s")',
                ipaddress,
                context_engine_id.prettyPrint(),
                context_name.prettyPrint(),
            )

            for name, val in var_binds:
                self._logger.log(VERBOSE, "%-40s = %s", name.prettyPrint(), val.prettyPrint())

    def _handle_unauthenticated_snmptrap(
        self,
        snmp_engine: pysnmp.entity.engine.SnmpEngine,
        execpoint: str,
        variables: Mapping[str, Any],
        cb_ctx: None,
    ) -> None:
        if (
            variables["securityLevel"] in {1, 2}
            and variables["statusInformation"]["errorIndication"]
            == pysnmp.proto.errind.unknownCommunityName
        ):
            msg = f"Unknown community ({variables['statusInformation'].get('communityName', '')})"
        elif (
            variables["securityLevel"] == 3
            and variables["statusInformation"]["errorIndication"]
            == pysnmp.proto.errind.unknownSecurityName
        ):
            msg = f"Unknown credentials (msgUserName: {variables['statusInformation'].get('msgUserName', '')})"
        else:
            msg = f"{variables['statusInformation']}"

        self._logger.log(
            VERBOSE,
            "Trap (v%d) dropped from %s: %s",
            variables["securityLevel"],
            variables["transportAddress"][0],
            msg,
        )


class SNMPTrapTranslator:
    def __init__(self, settings: Settings, config: Config, logger: Logger) -> None:
        self._logger = logger
        match config["translate_snmptraps"]:
            case False:
                self._mib_resolver: pysnmp.smi.view.MibViewController | None = None
                self.translate = self._translate_simple
            case (True, {**extra}) if not extra:  # matches empty dict
                self._mib_resolver = self._construct_resolver(
                    self._logger, settings.paths, load_texts=False
                )
                self.translate = self._translate_via_mibs
            case (True, {"add_description": True}):
                self._mib_resolver = self._construct_resolver(
                    self._logger, settings.paths, load_texts=True
                )
                self.translate = self._translate_via_mibs
            case _:
                raise Exception("invalid SNMP trap translation")

    @staticmethod
    def _construct_resolver(
        logger: Logger, paths: Paths, *, load_texts: bool
    ) -> pysnmp.smi.view.MibViewController | None:
        try:
            # manages python MIB modules
            builder = pysnmp.smi.builder.MibBuilder()

            # we need compiled Mib Dir and explicit system Mib Dir
            for source in [
                paths.local_mibs_dir,
                paths.checkmk_mibs_dir,
                paths.system_mibs_dir,
                paths.compiled_mibs_dir,
                paths.checkmk_compiled_mibs_dir,
            ]:
                builder.add_mib_sources(pysnmp.smi.builder.DirMibSource(source.value))

            # Indicate if we wish to load DESCRIPTION and other texts from MIBs
            builder.loadTexts = load_texts

            # This loads all or specified pysnmp MIBs into memory
            builder.load_modules()

            loaded_mib_module_names = list(builder.mibSymbols.keys())
            logger.info("Loaded %d SNMP MIB modules", len(loaded_mib_module_names))
            logger.log(VERBOSE, "Found modules: %s", ", ".join(loaded_mib_module_names))

            # This object maintains various indices built from MIBs data
            return pysnmp.smi.view.MibViewController(builder)
        except pysnmp.smi.error.SmiError:
            logger.info(
                "Exception while loading MIB modules. Proceeding without modules!", exc_info=True
            )
            return None

    def _translate_simple(self, ipaddress: str, var_bind_list: VarBinds) -> list[tuple[str, str]]:
        return [self._translate_binding_simple(oid, value) for oid, value in var_bind_list]

    @staticmethod
    def _translate_binding_simple(
        oid: pysnmp.proto.rfc1902.ObjectName, value: SimpleAsn1Type
    ) -> tuple[str, str]:
        key = "Uptime" if oid.asTuple() == (1, 3, 6, 1, 2, 1, 1, 3, 0) else str(oid)
        # We could use Asn1Type.isSuperTypeOf() instead of isinstance() below.
        if isinstance(value, pysnmp.proto.rfc1155.TimeTicks | pysnmp.proto.rfc1902.TimeTicks):
            val = _approx_age(float(value) / 100)
        else:
            val = value.prettyPrint()
        return key, val

    def _translate_via_mibs(self, ipaddress: str, var_bind_list: VarBinds) -> list[tuple[str, str]]:
        if self._mib_resolver is None:
            self._logger.warning("Failed to translate OIDs, no modules loaded (see above)")
            return self._translate_simple(ipaddress, var_bind_list)

        var_binds: list[tuple[str, str]] = []
        for oid, value in var_bind_list:
            try:
                translated_oid, translated_value = self._translate_binding_via_mibs(oid, value)
            except (pysnmp.smi.error.SmiError, pyasn1.error.ValueConstraintError):
                self._logger.warning(
                    "Failed to translate OID %s (in trap from %s): (enable debug logging for details)",
                    oid.prettyPrint(),
                    ipaddress,
                )
                self._logger.debug(
                    "Failed trap var binds:\n%s",
                    "\n".join(f"{i}: {repr(i)}" for i in var_bind_list),
                )
                self._logger.debug(traceback.format_exc())
                translated_oid = str(oid)
                translated_value = str(value)
            var_binds.append((translated_oid, translated_value))
        return var_binds

    def _translate_binding_via_mibs(
        self, oid: pysnmp.proto.rfc1902.ObjectName, value: SimpleAsn1Type
    ) -> tuple[str, str]:
        assert self._mib_resolver is not None
        # Disable mib_var[0] type detection
        mib_var = pysnmp.smi.rfc1902.ObjectType(
            pysnmp.smi.rfc1902.ObjectIdentity(oid),
            value,
        ).resolve_with_mib(self._mib_resolver)
        node = mib_var[0].get_mib_node()
        translated_oid = mib_var[0].prettyPrint().replace('"', "")
        translated_value = mib_var[1].prettyPrint()
        if units := getattr(node, "getUnits", str)():
            translated_value += f" {units}"
        if description := getattr(node, "getDescription", str)():
            translated_value += f"({description})"
        return translated_oid, translated_value


def compile_mib(
    *,
    mibname: str,
    content: str,
    source_dirs: Iterable[Path],
    search_dirs: Iterable[Path],
    destination_dir: Path,
) -> Mapping[str, MibStatus]:
    # Compile the uploaded SNMP MIB but also resolving dependencies and compiling dependents
    return (  # type: ignore[no-any-return]
        MibCompiler(
            SmiV1CompatParser(),
            PySnmpCodeGen(),
            PyFileWriter(destination_dir),
        )
        .add_sources(
            # Provides the just uploaded MIB module
            CallbackReader(lambda name, _context: content if name == mibname else "", None),
            # Directories containing ASN1 MIB files which may be used for dependency resolution
            *[FileReader(path) for path in source_dirs],
        )
        .add_searchers(
            # check for additional already compiled MIBs
            *[PyFileSearcher(path) for path in search_dirs],
            # check compiled MIBs shipped with PySNMP
            *[PyPackageSearcher(package) for package in PySnmpCodeGen.defaultMibPackages],
            # never recompile MIBs with MACROs
            StubSearcher(*PySnmpCodeGen.baseMibs),
        )
    ).compile(mibname, ignoreErrors=True, genTexts=True)


# Note: This is a local copy of the same function from cmk.utils.render, but for decoupling reasons
# we don't want to import that here: There is no fundamental reason to keep both versions in sync.
def _approx_age(secs: float) -> str:
    """Format time difference seconds into approximated human readable text"""
    if secs < 0:
        return f"-{_approx_age(-secs)}"
    if secs < 1e-12:
        return f"{secs * 1e15:.0f} fs"
    if secs < 1e-9:
        return f"{secs * 1e12:.0f} ps"
    if secs < 1e-6:
        return f"{secs * 1e9:.0f} ns"
    if secs < 1e-3:
        return f"{secs * 1e6:.0f} µs"
    if secs < 1:
        return f"{secs * 1e3:.0f} ms"
    if secs < 10:
        return f"{secs:.2f} s"
    if secs < 60:
        return f"{secs:.1f} s"
    if secs < 240:
        return f"{int(secs)} s"
    if (mins := secs / 60) < 360:
        return f"{int(mins)} m"
    if (hours := mins / 60) < 48:
        return f"{int(hours)} h"
    if (days := hours / 24) < 6:
        return f"{days:.1f}".removesuffix(".0") + " d"
    if days < 999:
        return f"{days:.0f} d"
    if (years := days / 365) < 10:
        return f"{years:.1f} y"
    return f"{years:.0f} y"
