// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableEventConsoleReplication.h"

#include <memory>

#include "livestatus/Column.h"
#include "livestatus/DynamicColumn.h"
#include "livestatus/DynamicEventConsoleReplicationColumn.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"

TableEventConsoleReplication::TableEventConsoleReplication(ICore *mc) {
    const ColumnOffsets offsets{};
    addDynamicColumn(std::make_unique<DynamicEventConsoleReplicationColumn>(
        "value", "The replication value", mc, offsets));
}

std::string TableEventConsoleReplication::name() const {
    return "eventconsolereplication";
}

std::string TableEventConsoleReplication::namePrefix() const {
    return "eventconsolereplication_";
}

void TableEventConsoleReplication::answerQuery(Query &query,
                                               const User & /*user*/,
                                               const ICore & /*core*/) {
    query.processDataset(Row{this});
}
