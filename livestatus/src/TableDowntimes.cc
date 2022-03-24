// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableDowntimes.h"

#include <chrono>
#include <map>
#include <memory>
#include <type_traits>

#include "ChronoUtils.h"
#include "Column.h"
#include "DowntimeOrComment.h"
#include "IntColumn.h"
#include "MonitoringCore.h"
#include "NagiosCore.h"
#include "Query.h"
#include "Row.h"
#include "StringColumn.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "TimeColumn.h"
#include "auth.h"
#include "nagios.h"  // IWYU pragma: keep

// TODO(sp): the dynamic data in this table must be locked with a mutex

TableDowntimes::TableDowntimes(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<Downtime>>(
        "author", "The contact that scheduled the downtime", offsets,
        [](const Downtime &r) { return r._author; }));
    addColumn(std::make_unique<StringColumn<Downtime>>(
        "comment", "A comment text", offsets,
        [](const Downtime &r) { return r._comment; }));
    addColumn(std::make_unique<IntColumn<Downtime>>(
        "id", "The id of the downtime", offsets,
        [](const Downtime &r) { return r._id; }));
    addColumn(std::make_unique<TimeColumn<Downtime>>(
        "entry_time", "The time the entry was made as UNIX timestamp", offsets,
        [](const Downtime &r) { return r._entry_time; }));
    addColumn(std::make_unique<IntColumn<Downtime>>(
        "type",
        "The type of the downtime: 0 if it is active, 1 if it is pending",
        offsets, [](const Downtime &r) { return r._type; }));
    addColumn(std::make_unique<BoolColumn<Downtime>>(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service", offsets,
        [](const Downtime &r) { return r._is_service; }));
    addColumn(std::make_unique<TimeColumn<Downtime>>(
        "start_time", "The start time of the downtime as UNIX timestamp",
        offsets, [](const Downtime &r) { return r._start_time; }));
    addColumn(std::make_unique<TimeColumn<Downtime>>(
        "end_time", "The end time of the downtime as UNIX timestamp", offsets,
        [](const Downtime &r) { return r._end_time; }));
    addColumn(std::make_unique<BoolColumn<Downtime>>(
        "fixed", "A 1 if the downtime is fixed, a 0 if it is flexible", offsets,
        [](const Downtime &r) { return r._fixed; }));
    addColumn(std::make_unique<BoolColumn<Downtime>>(
        "origin",
        "A 0 if the downtime has been set by a command, a 1 if it has been configured by a rule",
        offsets, [](const Downtime & /*r*/) { return false; }));
    addColumn(std::make_unique<IntColumn<Downtime>>(
        "recurring",
        "For recurring downtimes: 1: hourly, 2: daily, 3: weekly, 4: two-weekly, 5: four-weekly. Otherwise 0",
        offsets, [](const Downtime & /*r*/) { return 0; }));
    addColumn(std::make_unique<IntColumn<Downtime>>(
        "duration", "The duration of the downtime in seconds", offsets,
        [](const Downtime &r) {
            return mk::ticks<std::chrono::seconds>(r._duration);
        }));
    addColumn(std::make_unique<IntColumn<Downtime>>(
        "triggered_by",
        "The id of the downtime this downtime was triggered by or 0 if it was not triggered by another downtime",
        offsets, [](const Downtime &r) { return r._triggered_by; }));
    addColumn(std::make_unique<IntColumn<Downtime>>(
        "is_pending",
        "1 if the downtime is currently pending (not active), 0 if it is active",
        offsets, [](const Downtime &r) { return r._is_active ? 0 : 1; }));
    TableHosts::addColumns(this, "host_", offsets.add([](Row r) {
        return r.rawData<Downtime>()->_host;
    }));
    TableServices::addColumns(this, "service_", offsets.add([](Row r) {
        return r.rawData<Downtime>()->_service;
    }),
                              false /* no hosts table */);
}

std::string TableDowntimes::name() const { return "downtimes"; }

std::string TableDowntimes::namePrefix() const { return "downtime_"; }

void TableDowntimes::answerQuery(Query *query) {
    auto is_authorized = [service_auth = core()->serviceAuthorization(),
                          auth_user =
                              query->authUser()](const Downtime *downtime) {
        return downtime->_service == nullptr
                   ? is_authorized_for_hst(auth_user, downtime->_host)
                   : is_authorized_for_svc(service_auth, auth_user,
                                           downtime->_service);
    };

    for (const auto &[id, dt] : core()->impl<NagiosCore>()->_downtimes) {
        if (is_authorized(dt.get()) && !query->processDataset(Row{dt.get()})) {
            return;
        }
    }
}
