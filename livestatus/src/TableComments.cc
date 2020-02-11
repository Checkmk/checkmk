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
#include "Column.h"
#include "DowntimeOrComment.h"
#include "DowntimesOrComments.h"
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

TableComments::TableComments(MonitoringCore *mc) : Table(mc) {
    addColumn(std::make_unique<OffsetSStringColumn>(
        "author", "The contact that entered the comment",
        Column::Offsets{-1, -1, -1,
                        DANGEROUS_OFFSETOF(Comment, _author_name)}));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "comment", "A comment text",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(Comment, _comment)}));
    addColumn(std::make_unique<OffsetIntColumn>(
        "id", "The id of the comment",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(Comment, _id)}));
    addColumn(std::make_unique<OffsetTimeColumn>(
        "entry_time", "The time the entry was made as UNIX timestamp",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(Comment, _entry_time)}));
    addColumn(std::make_unique<OffsetIntColumn>(
        "type", "The type of the comment: 1 is host, 2 is service",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(Comment, _type)}));
    addColumn(std::make_unique<OffsetBoolColumn>(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(Comment, _is_service)}));

    addColumn(std::make_unique<OffsetIntColumn>(
        "persistent", "Whether this comment is persistent (0/1)",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(Comment, _persistent)}));
    addColumn(std::make_unique<OffsetIntColumn>(
        "source", "The source of the comment (0 is internal and 1 is external)",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(Comment, _source)}));
    addColumn(std::make_unique<OffsetIntColumn>(
        "entry_type",
        "The type of the comment: 1 is user, 2 is downtime, 3 is flap and 4 is acknowledgement",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(Comment, _entry_type)}));
    addColumn(std::make_unique<OffsetIntColumn>(
        "expires", "Whether this comment expires",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(Comment, _expires)}));
    addColumn(std::make_unique<OffsetTimeColumn>(
        "expire_time", "The time of expiry of this comment as a UNIX timestamp",
        Column::Offsets{-1, -1, -1,
                        DANGEROUS_OFFSETOF(Comment, _expire_time)}));

    TableHosts::addColumns(this, "host_", DANGEROUS_OFFSETOF(Comment, _host),
                           -1);
    TableServices::addColumns(this, "service_",
                              DANGEROUS_OFFSETOF(Comment, _service),
                              false /* no hosts table */);
}

std::string TableComments::name() const { return "comments"; }

std::string TableComments::namePrefix() const { return "comment_"; }

void TableComments::answerQuery(Query *query) {
    for (const auto &entry : core()->impl<Store>()->_comments) {
        if (!query->processDataset(Row(entry.second.get()))) {
            break;
        }
    }
}

bool TableComments::isAuthorized(Row row, const contact *ctc) const {
    auto dtc = rowData<DowntimeOrComment>(row);
    return is_authorized_for(core(), ctc, dtc->_host, dtc->_service);
}
