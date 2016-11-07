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
#include "DowntimeOrComment.h"
#include "DowntimesOrComments.h"  // IWYU pragma: keep
#include "MonitoringCore.h"
#include "OffsetIntColumn.h"
#include "OffsetSStringColumn.h"
#include "OffsetTimeColumn.h"
#include "Query.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "auth.h"

using std::string;

// TODO(sp): the dynamic data in this table must be locked with a mutex

TableDowntimes::TableDowntimes(const DowntimesOrComments &downtimes_holder,
                               const DowntimesOrComments &comments_holder,
                               MonitoringCore *core)
    : Table(core->loggerLivestatus()), _holder(downtimes_holder) {
    Downtime *ref = nullptr;
    addColumn(new OffsetSStringColumn(
        "author", "The contact that scheduled the downtime",
        reinterpret_cast<char *>(&(ref->_author_name)) -
            reinterpret_cast<char *>(ref)));
    addColumn(
        new OffsetSStringColumn("comment", "A comment text",
                                reinterpret_cast<char *>(&(ref->_comment)) -
                                    reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "id", "The id of the downtime",
        reinterpret_cast<char *>(&(ref->_id)) - reinterpret_cast<char *>(ref)));
    addColumn(new OffsetTimeColumn(
        "entry_time", "The time the entry was made as UNIX timestamp",
        reinterpret_cast<char *>(&(ref->_entry_time)) -
            reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "type",
        "The type of the downtime: 0 if it is active, 1 if it is pending",
        reinterpret_cast<char *>(&(ref->_type)) -
            reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service",
        reinterpret_cast<char *>(&(ref->_is_service)) -
            reinterpret_cast<char *>(ref)));

    addColumn(new OffsetTimeColumn(
        "start_time", "The start time of the downtime as UNIX timestamp",
        reinterpret_cast<char *>(&(ref->_start_time)) -
            reinterpret_cast<char *>(ref)));
    addColumn(new OffsetTimeColumn(
        "end_time", "The end time of the downtime as UNIX timestamp",
        reinterpret_cast<char *>(&(ref->_end_time)) -
            reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "fixed", "A 1 if the downtime is fixed, a 0 if it is flexible",
        reinterpret_cast<char *>(&(ref->_fixed)) -
            reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn("duration",
                                  "The duration of the downtime in seconds",
                                  reinterpret_cast<char *>(&(ref->_duration)) -
                                      reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "triggered_by",
        "The id of the downtime this downtime was triggered by or 0 if it was "
        "not triggered by another downtime",
        reinterpret_cast<char *>(&(ref->_triggered_by)) -
            reinterpret_cast<char *>(ref)));

    TableHosts::addColumns(
        this, "host_",
        reinterpret_cast<char *>(&(ref->_host)) - reinterpret_cast<char *>(ref),
        -1, downtimes_holder, comments_holder, core);
    TableServices::addColumns(
        this, "service_", reinterpret_cast<char *>(&(ref->_service)) -
                              reinterpret_cast<char *>(ref),
        false /* no hosts table */, downtimes_holder, comments_holder, core);
}

string TableDowntimes::name() const { return "downtimes"; }

string TableDowntimes::namePrefix() const { return "downtime_"; }

void TableDowntimes::answerQuery(Query *query) {
    for (const auto &entry : _holder) {
        if (!query->processDataset(entry.second.get())) {
            break;
        }
    }
}

bool TableDowntimes::isAuthorized(contact *ctc, void *data) {
    DowntimeOrComment *dtc = static_cast<DowntimeOrComment *>(data);
    return is_authorized_for(ctc, dtc->_host, dtc->_service);
}
