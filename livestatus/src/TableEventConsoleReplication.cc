// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableEventConsoleReplication.h"

#include <memory>

#include "Column.h"
#include "DynamicColumn.h"
#include "DynamicEventConsoleReplicationColumn.h"
#include "Query.h"
#include "Row.h"

TableEventConsoleReplication::TableEventConsoleReplication(MonitoringCore *mc)
    : Table(mc) {
    ColumnOffsets offsets{};
    addDynamicColumn(std::make_unique<DynamicEventConsoleReplicationColumn>(
        "value", "The replication value", mc, offsets));
}

std::string TableEventConsoleReplication::name() const {
    return "eventconsolereplication";
}

std::string TableEventConsoleReplication::namePrefix() const {
    return "eventconsolereplication_";
}

void TableEventConsoleReplication::answerQuery(Query *query,
                                               const User & /*user*/) {
    query->processDataset(Row(this));
}
