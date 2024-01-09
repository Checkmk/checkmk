// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableComments.h"

#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>

#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"
#include "livestatus/TableHosts.h"
#include "livestatus/TableServices.h"
#include "livestatus/TimeColumn.h"
#include "livestatus/User.h"

using row_type = IComment;

TableComments::TableComments(ICore *mc) {
    const ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<row_type>>(
        "author", "The contact that entered the comment", offsets,
        [](const row_type &row) { return row.author(); }));
    addColumn(std::make_unique<StringColumn<row_type>>(
        "comment", "A comment text", offsets,
        [](const row_type &row) { return row.comment(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "id", "The id of the comment", offsets,
        [](const row_type &row) { return row.id(); }));
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "entry_time", "The time the entry was made as UNIX timestamp", offsets,
        [](const row_type &row) { return row.entry_time(); }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service", offsets,
        [](const row_type &row) { return row.isService(); }));

    // Totally redundant column...
    addColumn(std::make_unique<IntColumn<row_type>>(
        "type", "The type of the comment: 1 is host, 2 is service", offsets,
        [](const row_type &row) { return row.isService() ? 2 : 1; }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "persistent", "Whether this comment is persistent (0/1)", offsets,
        [](const row_type &row) { return row.persistent(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "source", "The source of the comment (0 is internal and 1 is external)",
        offsets, [](const row_type &row) {
            return static_cast<int32_t>(row.source());
        }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "entry_type",
        "The type of the comment: 1 is user, 2 is downtime, 3 is flapping and 4 is acknowledgement",
        offsets, [](const row_type &row) {
            return static_cast<int32_t>(row.entry_type());
        }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "expires", "Whether this comment expires", offsets,
        [](const row_type &row) { return row.expires(); }));
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "expire_time", "The time of expiry of this comment as a UNIX timestamp",
        offsets, [](const row_type &row) { return row.expire_time(); }));

    TableHosts::addColumns(this, *mc, "host_", offsets.add([](Row r) {
        return &r.rawData<row_type>()->host();
    }),
                           LockComments::no, LockDowntimes::yes);
    TableServices::addColumns(
        this, *mc, "service_",
        offsets.add([](Row r) { return r.rawData<row_type>()->service(); }),
        TableServices::AddHosts::no, LockComments::no, LockDowntimes::yes);
}

std::string TableComments::name() const { return "comments"; }

std::string TableComments::namePrefix() const { return "comment_"; }

void TableComments::answerQuery(Query &query, const User &user,
                                const ICore &core) {
    core.all_of_comments([&query, &user](const row_type &row) {
        return !user.is_authorized_for_object(&row.host(), row.service(),
                                              false) ||
               query.processDataset(Row{&row});
    });
}
