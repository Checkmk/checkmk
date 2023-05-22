// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableDowntimes.h"

#include <chrono>
#include <cstdint>
#include <memory>
#include <variant>  // IWYU pragma: keep

#include "TableServices.h"
#include "livestatus/ChronoUtils.h"
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

// TODO(sp): the dynamic data in this table must be locked with a mutex

TableDowntimes::TableDowntimes(MonitoringCore *mc) : Table(mc) {
    const ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<IDowntime>>(
        "author", "The contact that scheduled the downtime", offsets,
        [](const IDowntime &r) { return r.author(); }));
    addColumn(std::make_unique<StringColumn<IDowntime>>(
        "comment", "A comment text", offsets,
        [](const IDowntime &r) { return r.comment(); }));
    addColumn(std::make_unique<IntColumn<IDowntime>>(
        "id", "The id of the downtime", offsets,
        [](const IDowntime &r) { return r.id(); }));
    addColumn(std::make_unique<TimeColumn<IDowntime>>(
        "entry_time", "The time the entry was made as UNIX timestamp", offsets,
        [](const IDowntime &r) { return r.entry_time(); }));
    // Totally redundant column...
    addColumn(std::make_unique<IntColumn<IDowntime>>(
        "type", "1 for a service downtime, 2 for a host downtime", offsets,
        [](const IDowntime &r) { return r.isService() ? 1 : 2; }));
    addColumn(std::make_unique<BoolColumn<IDowntime>>(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service", offsets,
        [](const IDowntime &r) { return r.isService(); }));
    addColumn(std::make_unique<TimeColumn<IDowntime>>(
        "start_time", "The start time of the downtime as UNIX timestamp",
        offsets, [](const IDowntime &r) { return r.start_time(); }));
    addColumn(std::make_unique<TimeColumn<IDowntime>>(
        "end_time", "The end time of the downtime as UNIX timestamp", offsets,
        [](const IDowntime &r) { return r.end_time(); }));
    addColumn(std::make_unique<BoolColumn<IDowntime>>(
        "fixed", "A 1 if the downtime is fixed, a 0 if it is flexible", offsets,
        [](const IDowntime &r) { return r.fixed(); }));
    addColumn(std::make_unique<BoolColumn<IDowntime>>(
        "origin",
        "A 0 if the downtime has been set by a command, a 1 if it has been configured by a rule",
        offsets, [](const IDowntime &r) { return r.origin_is_rule(); }));
    addColumn(std::make_unique<IntColumn<IDowntime>>(
        "recurring",
        "For recurring downtimes: 1: hourly, 2: daily, 3: weekly, 4: two-weekly, 5: four-weekly. Otherwise 0",
        offsets, [](const IDowntime &r) {
            return static_cast<int32_t>(r.recurring());
        }));
    addColumn(std::make_unique<IntColumn<IDowntime>>(
        "duration", "The duration of the downtime in seconds", offsets,
        [](const IDowntime &r) {
            return mk::ticks<std::chrono::seconds>(r.duration());
        }));
    addColumn(std::make_unique<IntColumn<IDowntime>>(
        "triggered_by",
        "The ID of the downtime triggering this downtime or 0 if there is none",
        offsets, [](const IDowntime &r) { return r.triggered_by(); }));
    addColumn(std::make_unique<BoolColumn<IDowntime>>(
        "is_pending",
        "1 if the downtime is currently pending (not active), 0 if it is active",
        offsets, [](const IDowntime &r) { return !r.pending(); }));
    TableHosts::addColumns(this, "host_", offsets.add([](Row r) {
        return &r.rawData<IDowntime>()->host();
    }),
                           LockComments::yes, LockDowntimes::no);
    TableServices::addColumns(
        this, "service_",
        offsets.add([](Row r) { return r.rawData<IDowntime>()->service(); }),
        TableServices::AddHosts::no, LockComments::yes, LockDowntimes::no);
}

std::string TableDowntimes::name() const { return "downtimes"; }

std::string TableDowntimes::namePrefix() const { return "downtime_"; }

void TableDowntimes::answerQuery(Query &query, const User &user) {
    core()->all_of_downtimes([&query, &user](const IDowntime &dt) {
        return !user.is_authorized_for_object(&dt.host(), dt.service(),
                                              false) ||
               query.processDataset(Row{&dt});
    });
}
