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

#include "TableComments.h"
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

TableComments::TableComments(const DowntimesOrComments &downtimes_holder,
                             const DowntimesOrComments &comments_holder,
                             MonitoringCore *core)
    : Table(core->loggerLivestatus()), _holder(comments_holder) {
    Comment *ref = nullptr;
    addColumn(new OffsetSStringColumn(
        "author", "The contact that entered the comment",
        reinterpret_cast<char *>(&(ref->_author_name)) -
            reinterpret_cast<char *>(ref)));
    addColumn(
        new OffsetSStringColumn("comment", "A comment text",
                                reinterpret_cast<char *>(&(ref->_comment)) -
                                    reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "id", "The id of the comment",
        reinterpret_cast<char *>(&(ref->_id)) - reinterpret_cast<char *>(ref)));
    addColumn(new OffsetTimeColumn(
        "entry_time", "The time the entry was made as UNIX timestamp",
        reinterpret_cast<char *>(&(ref->_entry_time)) -
            reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "type", "The type of the comment: 1 is host, 2 is service",
        reinterpret_cast<char *>(&(ref->_type)) -
            reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service",
        reinterpret_cast<char *>(&(ref->_is_service)) -
            reinterpret_cast<char *>(ref)));

    addColumn(new OffsetIntColumn(
        "persistent", "Whether this comment is persistent (0/1)",
        reinterpret_cast<char *>(&(ref->_persistent)) -
            reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "source", "The source of the comment (0 is internal and 1 is external)",
        reinterpret_cast<char *>(&(ref->_source)) -
            reinterpret_cast<char *>(ref)));
    addColumn(
        new OffsetIntColumn("entry_type",
                            "The type of the comment: 1 is user, 2 is "
                            "downtime, 3 is flap and 4 is acknowledgement",
                            reinterpret_cast<char *>(&(ref->_entry_type)) -
                                reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn("expires", "Whether this comment expires",
                                  reinterpret_cast<char *>(&(ref->_expires)) -
                                      reinterpret_cast<char *>(ref)));
    addColumn(new OffsetTimeColumn(
        "expire_time", "The time of expiry of this comment as a UNIX timestamp",
        reinterpret_cast<char *>(&(ref->_expire_time)) -
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

string TableComments::name() const { return "comments"; }

string TableComments::namePrefix() const { return "comment_"; }

void TableComments::answerQuery(Query *query) {
    for (const auto &entry : _holder) {
        if (!query->processDataset(entry.second.get())) {
            break;
        }
    }
}

bool TableComments::isAuthorized(contact *ctc, void *data) {
    DowntimeOrComment *dtc = static_cast<DowntimeOrComment *>(data);
    return is_authorized_for(ctc, dtc->_host, dtc->_service);
}
