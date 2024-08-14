// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableDowntimes.h"

#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>

#include "livestatus/ChronoUtils.h"
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

using row_type = IDowntime;

// TODO(sp): the dynamic data in this table must be locked with a mutex

TableDowntimes::TableDowntimes(ICore *mc) {
    const ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<row_type>>(
        "author", "The contact that scheduled the downtime", offsets,
        [](const row_type &row) { return row.author(); }));
    addColumn(std::make_unique<StringColumn<row_type>>(
        "comment", "A comment text", offsets,
        [](const row_type &row) { return row.comment(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "id", "The id of the downtime", offsets,
        [](const row_type &row) { return row.id(); }));
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "entry_time", "The time the entry was made as UNIX timestamp", offsets,
        [](const row_type &row) { return row.entry_time(); }));
    // Totally redundant column...
    addColumn(std::make_unique<IntColumn<row_type>>(
        "type", "1 for a service downtime, 2 for a host downtime", offsets,
        [](const row_type &row) { return row.isService() ? 1 : 2; }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service", offsets,
        [](const row_type &row) { return row.isService(); }));
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "start_time", "The start time of the downtime as UNIX timestamp",
        offsets, [](const row_type &row) { return row.start_time(); }));
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "end_time", "The end time of the downtime as UNIX timestamp", offsets,
        [](const row_type &row) { return row.end_time(); }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "fixed", "A 1 if the downtime is fixed, a 0 if it is flexible", offsets,
        [](const row_type &row) { return row.fixed(); }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "origin",
        "A 0 if the downtime has been set by a command, a 1 if it has been configured by a rule",
        offsets, [](const row_type &row) { return row.origin_is_rule(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "recurring",
        "For recurring downtimes: 1: hourly, 2: daily, 3: weekly, 4: two-weekly, 5: four-weekly. Otherwise 0",
        offsets, [](const row_type &row) {
            return static_cast<int32_t>(row.recurring());
        }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "duration", "The duration of the downtime in seconds", offsets,
        [](const row_type &row) {
            return mk::ticks<std::chrono::seconds>(row.duration());
        }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "triggered_by",
        "The ID of the downtime triggering this downtime or 0 if there is none",
        offsets, [](const row_type &row) { return row.triggered_by(); }));
    addColumn(std::make_unique<BoolColumn<row_type>>(
        "is_pending",
        "1 if the downtime is currently pending (not active), 0 if it is active",
        offsets, [](const row_type &row) { return row.pending(); }));
    TableHosts::addColumns(this, *mc, "host_", offsets.add([](Row r) {
        return &r.rawData<row_type>()->host();
    }),
                           LockComments::yes, LockDowntimes::no);
    TableServices::addColumns(
        this, *mc, "service_",
        offsets.add([](Row r) { return r.rawData<row_type>()->service(); }),
        TableServices::AddHosts::no, LockComments::yes, LockDowntimes::no);
}

std::string TableDowntimes::name() const { return "downtimes"; }

std::string TableDowntimes::namePrefix() const { return "downtime_"; }

void TableDowntimes::answerQuery(Query &query, const User &user,
                                 const ICore &core) {
    core.all_of_downtimes([&query, &user](const row_type &row) {
        return !user.is_authorized_for_object(&row.host(), row.service(),
                                              false) ||
               query.processDataset(Row{&row});
    });
}
