// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableComments.h"

#include <chrono>
#include <cstdint>
#include <memory>
#include <variant>

#include "TableServices.h"
#include "livestatus/Column.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/MonitoringCore.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"
#include "livestatus/TableHosts.h"
#include "livestatus/TimeColumn.h"
#include "livestatus/User.h"

TableComments::TableComments(MonitoringCore *mc) : Table(mc) {
    const ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<IComment>>(
        "author", "The contact that entered the comment", offsets,
        [](const IComment &r) { return r.author(); }));
    addColumn(std::make_unique<StringColumn<IComment>>(
        "comment", "A comment text", offsets,
        [](const IComment &r) { return r.comment(); }));
    addColumn(std::make_unique<IntColumn<IComment>>(
        "id", "The id of the comment", offsets,
        [](const IComment &r) { return r.id(); }));
    addColumn(std::make_unique<TimeColumn<IComment>>(
        "entry_time", "The time the entry was made as UNIX timestamp", offsets,
        [](const IComment &r) { return r.entry_time(); }));
    addColumn(std::make_unique<BoolColumn<IComment>>(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service", offsets,
        [](const IComment &r) { return r.isService(); }));

    // Totally redundant column...
    addColumn(std::make_unique<IntColumn<IComment>>(
        "type", "The type of the comment: 1 is host, 2 is service", offsets,
        [](const IComment &r) { return r.isService() ? 2 : 1; }));
    addColumn(std::make_unique<BoolColumn<IComment>>(
        "persistent", "Whether this comment is persistent (0/1)", offsets,
        [](const IComment &r) { return r.persistent(); }));
    addColumn(std::make_unique<IntColumn<IComment>>(
        "source", "The source of the comment (0 is internal and 1 is external)",
        offsets,
        [](const IComment &r) { return static_cast<int32_t>(r.source()); }));
    addColumn(std::make_unique<IntColumn<IComment>>(
        "entry_type",
        "The type of the comment: 1 is user, 2 is downtime, 3 is flapping and 4 is acknowledgement",
        offsets, [](const IComment &r) {
            return static_cast<int32_t>(r.entry_type());
        }));
    addColumn(std::make_unique<BoolColumn<IComment>>(
        "expires", "Whether this comment expires", offsets,
        [](const IComment &r) { return r.expires(); }));
    addColumn(std::make_unique<TimeColumn<IComment>>(
        "expire_time", "The time of expiry of this comment as a UNIX timestamp",
        offsets, [](const IComment &r) { return r.expire_time(); }));

    TableHosts::addColumns(this, "host_", offsets.add([](Row r) {
        return &r.rawData<IComment>()->host();
    }),
                           LockComments::no, LockDowntimes::yes);
    TableServices::addColumns(
        this, "service_",
        offsets.add([](Row r) { return r.rawData<IComment>()->service(); }),
        TableServices::AddHosts::no, LockComments::no, LockDowntimes::yes);
}

std::string TableComments::name() const { return "comments"; }

std::string TableComments::namePrefix() const { return "comment_"; }

void TableComments::answerQuery(Query &query, const User &user) {
    core()->all_of_comments([&query, &user](const IComment &r) {
        return !user.is_authorized_for_object(&r.host(), r.service(), false) ||
               query.processDataset(Row{&r});
    });
}
