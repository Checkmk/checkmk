// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableDowntimes.h"

#include <chrono>
#include <cstdint>
#include <memory>
#include <utility>

#include "BoolLambdaColumn.h"
#include "Column.h"
#include "DowntimeOrComment.h"
#include "DowntimesOrComments.h"
#include "IntLambdaColumn.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "Store.h"
#include "StringLambdaColumn.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "TimeLambdaColumn.h"
#include "auth.h"
#include "nagios.h"

// TODO(sp): the dynamic data in this table must be locked with a mutex

TableDowntimes::TableDowntimes(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    addColumn(std::make_unique<StringLambdaColumn<Downtime>>(
        "author", "The contact that scheduled the downtime", offsets,
        [](const Downtime &r) { return r._author_name; }));
    addColumn(std::make_unique<StringLambdaColumn<Downtime>>(
        "comment", "A comment text", offsets,
        [](const Downtime &r) { return r._comment; }));
    addColumn(std::make_unique<IntLambdaColumn<Downtime>>(
        "id", "The id of the downtime", offsets,
        [](const Downtime &r) { return r._id; }));
    addColumn(std::make_unique<TimeLambdaColumn<Downtime>>(
        "entry_time", "The time the entry was made as UNIX timestamp", offsets,
        [](const Downtime &r) {
            return std::chrono::system_clock::from_time_t(r._entry_time);
        }));
    addColumn(std::make_unique<IntLambdaColumn<Downtime>>(
        "type",
        "The type of the downtime: 0 if it is active, 1 if it is pending",
        offsets, [](const Downtime &r) { return r._type; }));
    addColumn(std::make_unique<BoolLambdaColumn<Downtime>>(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service", offsets,
        [](const Downtime &r) { return r._is_service; }));

    addColumn(std::make_unique<TimeLambdaColumn<Downtime>>(
        "start_time", "The start time of the downtime as UNIX timestamp",
        offsets, [](const Downtime &r) {
            return std::chrono::system_clock::from_time_t(r._start_time);
        }));
    addColumn(std::make_unique<TimeLambdaColumn<Downtime>>(
        "end_time", "The end time of the downtime as UNIX timestamp", offsets,
        [](const Downtime &r) {
            return std::chrono::system_clock::from_time_t(r._end_time);
        }));
    addColumn(std::make_unique<IntLambdaColumn<Downtime>>(
        "fixed", "A 1 if the downtime is fixed, a 0 if it is flexible", offsets,
        [](const Downtime &r) { return r._fixed; }));
    addColumn(std::make_unique<IntLambdaColumn<Downtime>>(
        "duration", "The duration of the downtime in seconds", offsets,
        [](const Downtime &r) { return r._duration; }));
    addColumn(std::make_unique<IntLambdaColumn<Downtime>>(
        "triggered_by",
        "The id of the downtime this downtime was triggered by or 0 if it was not triggered by another downtime",
        offsets, [](const Downtime &r) { return r._triggered_by; }));

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
    for (const auto &entry : core()->impl<Store>()->_downtimes) {
        // NOTE: Our typing is horrible here, so we need a downcast. Use
        // templates instead?
        const auto *r = static_cast<const Downtime *>(entry.second.get());
        if (!query->processDataset(Row(r))) {
            break;
        }
    }
}

bool TableDowntimes::isAuthorized(Row row, const contact *ctc) const {
    const auto *dtc = rowData<DowntimeOrComment>(row);
    return is_authorized_for(core(), ctc, dtc->_host, dtc->_service);
}
