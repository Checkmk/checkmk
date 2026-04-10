#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from logging import Logger

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import SNMPDetectSpecification
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.ccc.tty import format_warning
from cmk.helper_interface import FetcherError
from cmk.snmplib import (
    get_single_oid,
    SNMPBackend,
    SNMPDecodedString,
    SNMPDetectBaseType,
    SNMPSectionName,
)

type SNMPScanSection = tuple[SNMPSectionName, SNMPDetectBaseType]


@dataclass(frozen=True, kw_only=True)
class SNMPScanConfig:
    on_error: OnError
    missing_sys_description: bool


# gather auto_discovered check_plugin_names for this host
def gather_available_raw_section_names(
    sections: Collection[SNMPScanSection],
    *,
    scan_config: SNMPScanConfig,
    backend: SNMPBackend,
) -> frozenset[SNMPSectionName]:
    if not sections:
        return frozenset()

    try:
        return _snmp_scan(sections, scan_config=scan_config, backend=backend)
    except MKTimeout:
        raise
    except Exception as e:
        if scan_config.on_error is OnError.RAISE:
            raise
        if scan_config.on_error is OnError.WARN:
            backend.logger.error(f"SNMP scan failed: {e}")

    return frozenset()


OID_SYS_DESCR = ".1.3.6.1.2.1.1.1.0"
OID_SYS_OBJ = ".1.3.6.1.2.1.1.2.0"


def _snmp_scan(
    sections: Iterable[SNMPScanSection],
    *,
    scan_config: SNMPScanConfig,
    backend: SNMPBackend,
) -> frozenset[SNMPSectionName]:
    backend.logger.debug("  SNMP scan:")

    found_sections = _find_sections(
        sections,
        (
            _fake_description_object(backend.logger)
            if scan_config.missing_sys_description
            else _prefetch_description_object(backend=backend)
        ),
        on_error=scan_config.on_error,
        backend=backend,
    )
    _output_snmp_check_plugins("SNMP scan found", found_sections, backend.logger)
    return found_sections


def _prefetch_description_object(*, backend: SNMPBackend) -> Mapping[str, SNMPDecodedString]:
    def _fetch_required(oid: str, name: str) -> SNMPDecodedString:
        if (
            value := get_single_oid(
                oid,
                single_oid_cache={},
                backend=backend,
                log=backend.logger.debug,
            )
        ) is None:
            raise FetcherError(
                "Cannot fetch %s OID %s. Please check your SNMP "
                "configuration. Possible reason might be: Wrong credentials, "
                "wrong SNMP version, Firewall rules, etc." % (name, oid),
            )
        return value

    return {
        oid: _fetch_required(oid, name)
        for oid, name in (
            (OID_SYS_DESCR, "system description"),
            (OID_SYS_OBJ, "system object"),
        )
    }


def _fake_description_object(logger: Logger) -> Mapping[str, SNMPDecodedString]:
    """Fake OID values to prevent issues with a lot of scan functions"""
    logger.debug(
        f'       Skipping system description OID (Set {OID_SYS_DESCR} and {OID_SYS_OBJ} to "")'
    )
    return {OID_SYS_DESCR: "", OID_SYS_OBJ: ""}


def _find_sections(
    sections: Iterable[SNMPScanSection],
    initial_system_oids: Mapping[str, SNMPDecodedString],
    *,
    on_error: OnError,
    backend: SNMPBackend,
) -> frozenset[SNMPSectionName]:
    found_sections: set[SNMPSectionName] = set()
    for name, specs in sections:
        oid_value_getter = functools.partial(
            get_single_oid,
            section_name=name,
            single_oid_cache={**initial_system_oids},
            backend=backend,
            log=backend.logger.debug,
        )
        try:
            if evaluate_snmp_detection(
                # It was an `SNMPDetectSpecification` all along, we forgot the type.
                # Historic reasons, can be cleaned up.
                detect_spec=SNMPDetectSpecification(specs),
                oid_value_getter=oid_value_getter,
            ):
                found_sections.add(name)
        except MKTimeout:
            raise
        except MKGeneralException:
            # some error messages which we explicitly want to show to the user
            # should be raised through this
            raise
        except Exception:
            if on_error is OnError.RAISE:
                raise
            if on_error is OnError.WARN:
                backend.logger.warning(
                    format_warning(f"   Exception in SNMP scan function of {name}")
                )
    return frozenset(found_sections)


def _output_snmp_check_plugins(
    title: str, collection: Collection[SNMPSectionName], logger: Logger
) -> None:
    collection_out = " ".join(str(n) for n in sorted(collection)) if collection else "-"
    logger.debug(
        "   %-35s%s%s%s%s"
        % (
            title,
            tty.bold,
            tty.yellow,
            collection_out,
            tty.normal,
        )
    )
