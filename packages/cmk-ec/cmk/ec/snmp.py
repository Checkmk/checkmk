#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: We *really* need type stubs or a typed version of the SNMP libraries...
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-untyped-call"

import time
from collections.abc import Iterable, Mapping, Sequence
from logging import DEBUG, Logger
from typing import Any, override

import pysnmp.carrier.base
import pysnmp.debug
import pysnmp.entity.config
import pysnmp.entity.engine
import pysnmp.entity.rfc3413.ntfrcv
import pysnmp.proto.api
import pysnmp.proto.errind
import pysnmp.proto.rfc1155
import pysnmp.proto.rfc1902
import pysnmp.proto.rfc3411
import pysnmp.proto.secmod.cache
import pysnmp.smi.builder
import pysnmp.smi.error
import pysnmp.smi.rfc1902
import pysnmp.smi.view
from pyasn1.type.base import SimpleAsn1Type

from cmk.ccc.log import VERBOSE

from .config import AuthenticationProtocol, Config, PrivacyProtocol
from .event import scrub_string
from .settings import Paths, Settings

VarBind = tuple[pysnmp.proto.rfc1902.ObjectName, SimpleAsn1Type]
VarBinds = Sequence[VarBind]


class _PySnmpDebug(pysnmp.debug.Debug):
    """PySNMP's debug messages, formatted only when debugging"""

    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        # The MIB view ones fail for string DEFVALs.
        super().__init__("all", "!mibview", printer=logger.debug)

    @override
    def __and__(self, flag: int) -> int:
        return int(super().__and__(flag)) if self._logger.isEnabledFor(DEBUG) else 0

    @override
    def __rand__(self, flag: int) -> int:
        return self & flag

    def __bool__(self) -> bool:
        """For PySNMP's MIB instrumentation, which tests the logger, not a flag"""
        return self._logger.isEnabledFor(DEBUG)


class _DroppingTransportDispatcher(pysnmp.carrier.base.AbstractTransportDispatcher):
    """Drops what PySNMP sends, e.g. reports: We only receive traps."""

    @override
    def send_message(self, *_: object) -> None:
        pass


def _snmp_version(security_model: int) -> str:
    """SNMPv1, SNMPv2c and SNMPv3 have the security models 1, 2 and 3."""
    return "v2c" if security_model == 2 else f"v{security_model}"


class SNMPTrapParser:
    # Only traps: _drop_request() drops INFORMs like the other requests.
    class _ECNotificationReceiver(pysnmp.entity.rfc3413.ntfrcv.NotificationReceiver):
        SUPPORTED_PDU_TYPES = (
            pysnmp.proto.api.v1.TrapPDU.tagSet,
            pysnmp.proto.api.v2c.SNMPv2TrapPDU.tagSet,
        )  # type: ignore[assignment]

        error: Exception | None = None

        @override
        def process_pdu(self, *args: Any, **kwargs: Any) -> None:
            """Keeps failures, PySNMP would skip its cleanup for them"""
            try:
                super().process_pdu(*args, **kwargs)
            except Exception as e:
                self.error = e

    def __init__(self, settings: Settings, config: Config, logger: Logger) -> None:
        self._logger = logger

        # Hand over our logger to PySNMP
        pysnmp.debug.set_logger(_PySnmpDebug(logger))

        self.snmp_engine = pysnmp.entity.engine.SnmpEngine()
        self.snmp_engine.register_transport_dispatcher(_DroppingTransportDispatcher())
        self._initialize_snmp_credentials(config)
        # NOTE: pysnmp has a really strange notification receiver API: The constructor call below
        # effectively registers the callback (2nd argument) at the SNMP engine. The callback stores
        # the parsed trap in _varbinds_and_ipaddress when parse() is called.
        self._receiver = SNMPTrapParser._ECNotificationReceiver(
            self.snmp_engine,
            self._handle_snmptrap,
        )
        # PySNMP leaks unhandled SNMPv1/v2c requests.
        # TODO: Remove after https://github.com/lextudio/pysnmp/pull/261
        self.snmp_engine.message_dispatcher.register_context_engine_id(
            b"", pysnmp.proto.rfc3411.CONFIRMED_CLASS_PDUS, self._drop_request
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
                self._logger.info(
                    "adding SNMPv1 system: communityIndex=%(community_index)s",
                    {"community_index": community_index},
                )
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
                    "adding SNMPv3 user: userName=%(user_id)s, authProtocol=%(auth_proto)s, "
                    "privProtocol=%(priv_proto)s, securityEngineId=%(engine_id)s",
                    {
                        "user_id": user_id,
                        "auth_proto": ".".join(str(i) for i in auth_proto),
                        "priv_proto": ".".join(str(i) for i in priv_proto),
                        "engine_id": engine_id,
                    },
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
        """Let PySNMP parse the given trap data. The _handle_snmptrap() callback below collects the result.

        Drops what PySNMP doesn't accept, raises failures of accepted traps.
        """
        self._logger.log(
            VERBOSE,
            "Trap received from %(host)s:%(port)d. Checking for acceptance now.",
            {"host": sender_address[0], "port": sender_address[1]},
        )
        self._varbinds_and_ipaddress = None
        self._receiver.error = None
        self.snmp_engine.set_user_context(sender_address=sender_address)
        try:
            self.snmp_engine.message_dispatcher.receive_message(
                snmpEngine=self.snmp_engine,
                transportDomain=(),
                transportAddress=sender_address,
                wholeMsg=data,
            )
        except Exception as e:
            # Senders trigger these, e.g. with b"hello world".
            self._logger.log(
                VERBOSE,
                "Message dropped from %(host)s, PySNMP failed on it: %(error_type)s: %(error)s",
                {"host": sender_address[0], "error_type": type(e).__name__, "error": e},
                exc_info=self._logger.isEnabledFor(DEBUG),
            )
            return None
        finally:
            # PySNMP forgets SNMPv3 senders only on timer ticks: Tick once per message.
            now = time.time()
            for message_processing in self.snmp_engine.message_processing_subsystems.values():
                message_processing.receive_timer_tick(self.snmp_engine, now)
            for security_model in self.snmp_engine.security_models.values():
                security_model.receive_timer_tick(self.snmp_engine, now)
            # PySNMP leaks the state of some failing SNMPv3 messages, and none is pending here.
            usm = self.snmp_engine.security_models[3]
            if not usm._cache.is_empty():  # noqa: SLF001
                usm._cache = pysnmp.proto.secmod.cache.Cache()  # noqa: SLF001
        if (error := self._receiver.error) is not None:
            raise error
        return self._varbinds_and_ipaddress

    def _handle_snmptrap(
        self,
        snmp_engine: pysnmp.entity.engine.SnmpEngine,  # noqa: ARG002
        state_reference: str,  # noqa: ARG002
        context_engine_id: pysnmp.smi.rfc1902.ObjectIdentity,
        context_name: pysnmp.proto.rfc1902.ObjectName,
        var_binds: VarBinds,
        cb_ctx: None,  # noqa: ARG002
    ) -> None:
        # sender_address contains a (host: str, port: int) tuple
        ipaddress: str = self.snmp_engine.get_user_context("sender_address")[0]  # type: ignore[index]
        self._log_snmptrap_details(context_engine_id, context_name, var_binds, ipaddress)
        trap = self._snmp_trap_translator.translate(ipaddress, var_binds)
        # NOTE: There can be only one trap per PDU, so we don't run into the risk of overwriting previous info.
        self._varbinds_and_ipaddress = trap, ipaddress

    def _drop_request(
        self,
        snmp_engine: pysnmp.entity.engine.SnmpEngine,
        message_processing_model: int,
        security_model: int,
        security_name: pysnmp.proto.rfc1902.OctetString,  # noqa: ARG002
        security_level: int,  # noqa: ARG002
        context_engine_id: pysnmp.proto.rfc1902.OctetString,  # noqa: ARG002
        context_name: pysnmp.proto.rfc1902.OctetString,  # noqa: ARG002
        pdu_version: int,  # noqa: ARG002
        pdu: Any,
        max_size_response_scoped_pdu: int,  # noqa: ARG002
        state_reference: int,
    ) -> None:
        """Drops a request without leaking PySNMP's state of it"""
        subsystems = snmp_engine.message_processing_subsystems
        # PySNMP types the keys as pyasn1 Integers, which hash like ints.
        message_processing = subsystems[message_processing_model]  # type: ignore[index]
        # There is no API for it.
        state = message_processing._cache.pop_by_state_reference(state_reference)  # noqa: SLF001
        snmp_engine.security_models[security_model].release_state_information(
            state["securityStateReference"]
        )
        self._logger.log(
            VERBOSE,
            "%(pdu_type)s (%(version)s) dropped from %(host)s, only traps are supported",
            {
                "pdu_type": self._pdu_name(pdu),
                "version": _snmp_version(int(security_model)),
                "host": snmp_engine.get_user_context("sender_address")[0],  # type: ignore[index]
            },
        )

    @staticmethod
    def _pdu_name(pdu: Any) -> str:
        """What we call a PDU in log messages"""
        return type(pdu).__name__.removesuffix("PDU")

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
                'Trap accepted from %(ipaddress)s (ContextEngineId "%(context_engine_id)s", '
                'SNMPContext "%(context_name)s")',
                {
                    "ipaddress": ipaddress,
                    "context_engine_id": context_engine_id.prettyPrint(),
                    "context_name": context_name.prettyPrint(),
                },
            )

            for name, val in var_binds:
                self._logger.log(
                    VERBOSE,
                    "%(name)-40s = %(type)s %(value)s",
                    {
                        "name": name.prettyPrint(),
                        "type": type(val).__name__,
                        "value": val.prettyPrint(),
                    },
                )

    def _handle_unauthenticated_snmptrap(
        self,
        snmp_engine: pysnmp.entity.engine.SnmpEngine,  # noqa: ARG002
        execpoint: str,  # noqa: ARG002
        variables: Mapping[str, Any],
        cb_ctx: None,  # noqa: ARG002
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
            "Trap (v%(security_level)d) dropped from %(transport_address)s: %(msg)s",
            {
                "security_level": variables["securityLevel"],
                "transport_address": variables["transportAddress"][0],
                "msg": msg,
            },
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

            # Load each MIB module individually so that a single failure doesn't
            # prevent the remaining modules from being loaded.
            for mib_source in builder.get_mib_sources():
                for module_name in mib_source.listdir():
                    try:
                        builder.load_module(module_name)
                    except pysnmp.smi.error.MibNotFoundError as e:
                        logger.warning(
                            "Skipping MIB module %(module_name)s: missing dependency (%(error)s)",
                            {"module_name": module_name, "error": e},
                        )
                    except pysnmp.smi.error.SmiError:
                        logger.warning(
                            "Failed to load MIB module %(module_name)s",
                            {"module_name": module_name},
                            exc_info=True,
                        )

            loaded_mib_module_names = list(builder.mibSymbols.keys())
            logger.info(
                "Loaded %(count)d SNMP MIB modules", {"count": len(loaded_mib_module_names)}
            )
            logger.log(
                VERBOSE,
                "Found modules: %(modules)s",
                {"modules": ", ".join(loaded_mib_module_names)},
            )

            # This object maintains various indices built from MIBs data
            return pysnmp.smi.view.MibViewController(builder)
        except pysnmp.smi.error.SmiError:
            logger.info(
                "Exception while loading MIB modules. Proceeding without modules!", exc_info=True
            )
            return None

    def _translate_simple(self, ipaddress: str, var_bind_list: VarBinds) -> list[tuple[str, str]]:  # noqa: ARG002
        return [self._translate_binding_simple(oid, value) for oid, value in var_bind_list]

    @staticmethod
    def _translate_binding_simple(
        oid: pysnmp.proto.rfc1902.ObjectName, value: SimpleAsn1Type
    ) -> tuple[str, str]:
        key = "Uptime" if oid.asTuple() == (1, 3, 6, 1, 2, 1, 1, 3, 0) else str(oid)
        # pysnmp converts the var binds of SNMPv1 traps to SNMPv2 types, but the sysUpTime.0 it
        # adds from the header of such a trap keeps its SNMPv1 type.
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
            # PySNMP and compiled MIBs fail in many ways, so keep the trap.
            except Exception as e:
                self._logger.warning(
                    "Failed to translate OID %(oid)s in trap from %(ipaddress)s, "
                    "keeping it untranslated: %(error_type)s: %(error)s "
                    "(enable debug logging for details)",
                    {
                        "oid": oid.prettyPrint(),
                        "ipaddress": ipaddress,
                        "error_type": type(e).__name__,
                        "error": e,
                    },
                )
                self._logger.debug(
                    "Failed to translate OID %(oid)s", {"oid": oid.prettyPrint()}, exc_info=True
                )
                translated_oid, translated_value = self._translate_binding_raw(oid, value)
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

    @staticmethod
    def _translate_binding_raw(
        oid: pysnmp.proto.rfc1902.ObjectName, value: SimpleAsn1Type
    ) -> tuple[str, str]:
        # str() decodes octet strings as Latin-1, which garbles IP addresses and binary data.
        # prettyPrint() shows any text with a non-ASCII or control character in hex, so use it
        # only for IP addresses and for values whose event text would contain C0 control
        # characters other than CR. This turns some text into hex, too, e.g. with escape
        # sequences or in UTF-16, but we can't tell it apart from binary data.
        # pysnmp converts the var binds of SNMPv1 traps to SNMPv2 types, but the snmpTrapAddress.0
        # it adds from the header of such a trap keeps its SNMPv1 type.
        if not isinstance(value, pysnmp.proto.rfc1155.IpAddress | pysnmp.proto.rfc1902.IpAddress):
            text = str(value)
            if all(c >= " " or c == "\r" for c in scrub_string(text)):
                return str(oid), text
        return str(oid), value.prettyPrint()


def trap_error_text(error: Exception) -> str:
    """For log messages, as a KeyError shows its key's repr, for pyasn1 values all of its type"""
    if (
        isinstance(error, KeyError)
        and len(error.args) == 1
        and isinstance(key := error.args[0], SimpleAsn1Type)
    ):
        return str(key.prettyPrint())
    return str(error)


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
