// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableDowntimes.h"
#include <memory>
#include <utility>
#include "Column.h"
#include "DowntimeOrComment.h"
#include "MonitoringCore.h"
#include "OffsetBoolColumn.h"
#include "OffsetIntColumn.h"
#include "OffsetSStringColumn.h"
#include "OffsetTimeColumn.h"
#include "Query.h"
#include "Row.h"
#include "Store.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "auth.h"
#include "nagios.h"

// TODO(sp): the dynamic data in this table must be locked with a mutex

TableDowntimes::TableDowntimes(MonitoringCore *mc) : Table(mc) {
    addColumn(std::make_unique<OffsetSStringColumn>(
        "author", "The contact that scheduled the downtime", -1, -1, -1,
        DANGEROUS_OFFSETOF(Downtime, _author_name)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "comment", "A comment text", -1, -1, -1,
        DANGEROUS_OFFSETOF(Downtime, _comment)));
    addColumn(std::make_unique<OffsetIntColumn>(
        "id", "The id of the downtime", -1, -1, -1,
        DANGEROUS_OFFSETOF(Downtime, _id)));
    addColumn(std::make_unique<OffsetTimeColumn>(
        "entry_time", "The time the entry was made as UNIX timestamp", -1, -1,
        -1, DANGEROUS_OFFSETOF(Downtime, _entry_time)));
    addColumn(std::make_unique<OffsetIntColumn>(
        "type",
        "The type of the downtime: 0 if it is active, 1 if it is pending", -1,
        -1, -1, DANGEROUS_OFFSETOF(Downtime, _type)));
    addColumn(std::make_unique<OffsetBoolColumn>(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service", -1, -1, -1,
        DANGEROUS_OFFSETOF(Downtime, _is_service)));

    addColumn(std::make_unique<OffsetTimeColumn>(
        "start_time", "The start time of the downtime as UNIX timestamp", -1,
        -1, -1, DANGEROUS_OFFSETOF(Downtime, _start_time)));
    addColumn(std::make_unique<OffsetTimeColumn>(
        "end_time", "The end time of the downtime as UNIX timestamp", -1, -1,
        -1, DANGEROUS_OFFSETOF(Downtime, _end_time)));
    addColumn(std::make_unique<OffsetIntColumn>(
        "fixed", "A 1 if the downtime is fixed, a 0 if it is flexible", -1, -1,
        -1, DANGEROUS_OFFSETOF(Downtime, _fixed)));
    addColumn(std::make_unique<OffsetIntColumn>(
        "duration", "The duration of the downtime in seconds", -1, -1, -1,
        DANGEROUS_OFFSETOF(Downtime, _duration)));
    addColumn(std::make_unique<OffsetIntColumn>(
        "triggered_by",
        "The id of the downtime this downtime was triggered by or 0 if it was not triggered by another downtime",
        -1, -1, -1, DANGEROUS_OFFSETOF(Downtime, _triggered_by)));

    TableHosts::addColumns(this, mc, "host_",
                           DANGEROUS_OFFSETOF(Downtime, _host), -1);
    TableServices::addColumns(this, mc, "service_",
                              DANGEROUS_OFFSETOF(Downtime, _service),
                              false /* no hosts table */);
}

std::string TableDowntimes::name() const { return "downtimes"; }

std::string TableDowntimes::namePrefix() const { return "downtime_"; }

void TableDowntimes::answerQuery(Query *query) {
    for (const auto &entry : core()->impl<Store>()->_downtimes) {
        if (!query->processDataset(Row(entry.second.get()))) {
            break;
        }
    }
}

bool TableDowntimes::isAuthorized(Row row, const contact *ctc) const {
    auto dtc = rowData<DowntimeOrComment>(row);
    return is_authorized_for(core(), ctc, dtc->_host, dtc->_service);
}
