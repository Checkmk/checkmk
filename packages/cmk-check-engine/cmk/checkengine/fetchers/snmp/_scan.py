#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import logging
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import SNMPDetectSpecification
from cmk.ccc.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.checkengine.fetcher_abc import FetcherError
from cmk.checkengine.snmplib import (
    get_single_oid,
    SNMPBackend,
    SNMPDecodedString,
    SNMPDetectBaseType,
    SNMPSectionName,
)

type SNMPScanSection = tuple[SNMPSectionName, SNMPDetectBaseType]
logger = logging.getLogger(__name__)


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
    debug: bool,
) -> frozenset[SNMPSectionName]:
    if not sections:
        return frozenset()

    try:
        return _snmp_scan(sections, scan_config=scan_config, backend=backend, debug=debug)
    except MKTimeout:
        raise
    except Exception:
        if scan_config.on_error is OnError.RAISE:
            raise
        if scan_config.on_error is OnError.WARN:
            logger.exception("SNMP scan failed")

    return frozenset()


OID_SYS_DESCR = ".1.3.6.1.2.1.1.1.0"
OID_SYS_OBJ = ".1.3.6.1.2.1.1.2.0"


def _snmp_scan(
    sections: Iterable[SNMPScanSection],
    *,
    scan_config: SNMPScanConfig,
    backend: SNMPBackend,
    debug: bool,
) -> frozenset[SNMPSectionName]:
    logger.debug("SNMP scan:")

    found_sections = _find_sections(
        sections,
        (
            _fake_description_object()
            if scan_config.missing_sys_description
            else _prefetch_description_object(backend=backend, debug=debug)
        ),
        on_error=scan_config.on_error,
        backend=backend,
        debug=debug,
    )
    _output_snmp_check_plugins("SNMP scan found", found_sections)
    return found_sections


def _prefetch_description_object(
    *, backend: SNMPBackend, debug: bool
) -> Mapping[str, SNMPDecodedString]:
    def _fetch_required(oid: str, name: str) -> SNMPDecodedString:
        if (
            value := get_single_oid(oid, single_oid_cache={}, backend=backend, debug=debug)
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


def _fake_description_object() -> Mapping[str, SNMPDecodedString]:
    """Fake OID values to prevent issues with a lot of scan functions"""
    logger.debug(
        'Skipping system description OID (Set %(sys_descr)s and %(sys_obj)s to "")',
        {"sys_descr": OID_SYS_DESCR, "sys_obj": OID_SYS_OBJ},
    )
    return {OID_SYS_DESCR: "", OID_SYS_OBJ: ""}


def _find_sections(
    sections: Iterable[SNMPScanSection],
    initial_system_oids: Mapping[str, SNMPDecodedString],
    *,
    on_error: OnError,
    backend: SNMPBackend,
    debug: bool,
) -> frozenset[SNMPSectionName]:
    found_sections: set[SNMPSectionName] = set()
    for name, specs in sections:
        oid_value_getter = functools.partial(
            get_single_oid,
            section_name=name,
            single_oid_cache={**initial_system_oids},
            backend=backend,
            warn_on_empty_value=False,  # During discovery, this is not worth a warning
            debug=debug,
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
                logger.exception("Exception in SNMP scan function of %(name)s", {"name": name})
    return frozenset(found_sections)


def _output_snmp_check_plugins(title: str, collection: Collection[SNMPSectionName]) -> None:
    collection_out = " ".join(str(n) for n in sorted(collection)) if collection else "-"
    logger.debug(
        "%(title)-35s%(collection)s",
        {
            "title": title,
            "collection": collection_out,
        },
    )
