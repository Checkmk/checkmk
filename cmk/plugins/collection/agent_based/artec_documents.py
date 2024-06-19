#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    equals,
    get_rate,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

# .1.3.6.1.4.1.31560.0.0.3.1.3.1.48 Amount Documents Count --> ARTEC-MIB::artecDocumentsName.1.48
# .1.3.6.1.4.1.31560.0.0.3.1.3.1.49 Replicate Count        --> ARTEC-MIB::artecDocumentsName.1.49
# .1.3.6.1.4.1.31560.0.0.3.1.3.1.50 Sign count             --> ARTEC-MIB::artecDocumentsName.1.50
# .1.3.6.1.4.1.31560.0.0.3.1.1.1.48 8861531                --> ARTEC-MIB::artecDocumentsValues.1.48
# .1.3.6.1.4.1.31560.0.0.3.1.1.1.49 1653573                --> ARTEC-MIB::artecDocumentsValues.1.49
# .1.3.6.1.4.1.31560.0.0.3.1.1.1.50 8861118                --> ARTEC-MIB::artecDocumentsValues.1.50


def inventory_artec_documents(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_artec_documents(section: StringTable) -> CheckResult:
    now = time.time()
    for doc_name, doc_val_str in section:
        if doc_val_str:
            documents = int(doc_val_str)
            name = doc_name.replace("Count", "").replace("count", "").strip()
            rate = get_rate(get_value_store(), doc_name, now, documents, raise_overflow=True)
            yield Result(state=State.OK, summary="%s: %d (%.2f/s)" % (name, documents, rate))


def parse_artec_documents(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_artec_documents = SimpleSNMPSection(
    name="artec_documents",
    detect=all_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        contains(".1.3.6.1.2.1.1.1.0", "version"),
        contains(".1.3.6.1.2.1.1.1.0", "serial"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.31560.0.0.3.1",
        oids=["3", "1"],
    ),
    parse_function=parse_artec_documents,
)
check_plugin_artec_documents = CheckPlugin(
    name="artec_documents",
    service_name="Documents",
    discovery_function=inventory_artec_documents,
    check_function=check_artec_documents,
)
