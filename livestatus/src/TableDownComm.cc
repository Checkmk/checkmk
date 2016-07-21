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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableDownComm.h"
#include "DowntimeOrComment.h"
#include "OffsetIntColumn.h"
#include "OffsetStringColumn.h"
#include "OffsetTimeColumn.h"
#include "Query.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "auth.h"
#include "logger.h"

using std::make_pair;

// Todo: the dynamic data in this table must be
// locked with a mutex

TableDownComm::TableDownComm(bool is_downtime) {
    if (is_downtime) {
        _name = "downtimes";
    } else {
        _name = "comments";
    }
    DowntimeOrComment *ref = nullptr;
    addColumn(new OffsetStringColumn(
        "author", is_downtime ? "The contact that scheduled the downtime"
                              : "The contact that entered the comment",
        reinterpret_cast<char *>(&(ref->_author_name)) -
            reinterpret_cast<char *>(ref)));
    addColumn(
        new OffsetStringColumn("comment", "A comment text",
                               reinterpret_cast<char *>(&(ref->_comment)) -
                                   reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "id", is_downtime ? "The id of the downtime" : "The id of the comment",
        reinterpret_cast<char *>(&(ref->_id)) - reinterpret_cast<char *>(ref)));
    addColumn(new OffsetTimeColumn(
        "entry_time", "The time the entry was made as UNIX timestamp",
        reinterpret_cast<char *>(&(ref->_entry_time)) -
            reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "type",
        is_downtime
            ? "The type of the downtime: 0 if it is active, 1 if it is pending"
            : "The type of the comment: 1 is host, 2 is service",
        reinterpret_cast<char *>(&(ref->_type)) -
            reinterpret_cast<char *>(ref)));
    addColumn(new OffsetIntColumn(
        "is_service",
        "0, if this entry is for a host, 1 if it is for a service",
        reinterpret_cast<char *>(&(ref->_is_service)) -
            reinterpret_cast<char *>(ref)));

    if (is_downtime) {
        Downtime *ref = nullptr;
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
        addColumn(new OffsetIntColumn(
            "duration", "The duration of the downtime in seconds",
            reinterpret_cast<char *>(&(ref->_duration)) -
                reinterpret_cast<char *>(ref)));
        addColumn(new OffsetIntColumn(
            "triggered_by",
            "The id of the downtime this downtime was triggered by or 0 if it "
            "was not triggered by another downtime",
            reinterpret_cast<char *>(&(ref->_triggered_by)) -
                reinterpret_cast<char *>(ref)));
    } else {
        Comment *ref = nullptr;
        addColumn(new OffsetIntColumn(
            "persistent", "Whether this comment is persistent (0/1)",
            reinterpret_cast<char *>(&(ref->_persistent)) -
                reinterpret_cast<char *>(ref)));
        addColumn(new OffsetIntColumn(
            "source",
            "The source of the comment (0 is internal and 1 is external)",
            reinterpret_cast<char *>(&(ref->_source)) -
                reinterpret_cast<char *>(ref)));
        addColumn(
            new OffsetIntColumn("entry_type",
                                "The type of the comment: 1 is user, 2 is "
                                "downtime, 3 is flap and 4 is acknowledgement",
                                reinterpret_cast<char *>(&(ref->_entry_type)) -
                                    reinterpret_cast<char *>(ref)));
        addColumn(
            new OffsetIntColumn("expires", "Whether this comment expires",
                                reinterpret_cast<char *>(&(ref->_expires)) -
                                    reinterpret_cast<char *>(ref)));
        addColumn(new OffsetTimeColumn(
            "expire_time",
            "The time of expiry of this comment as a UNIX timestamp",
            reinterpret_cast<char *>(&(ref->_expire_time)) -
                reinterpret_cast<char *>(ref)));
    }

    TableHosts::addColumns(this, "host_",
                           reinterpret_cast<char *>(&(ref->_host)) -
                               reinterpret_cast<char *>(ref));
    TableServices::addColumns(this, "service_",
                              reinterpret_cast<char *>(&(ref->_service)) -
                                  reinterpret_cast<char *>(ref),
                              false /* no hosts table */);
}

TableDownComm::~TableDownComm() {
    for (auto &entry : _entries) {
        delete entry.second;
    }
}

void TableDownComm::addComment(nebstruct_comment_data *data) {
    if (data->type == NEBTYPE_COMMENT_ADD ||
        data->type == NEBTYPE_COMMENT_LOAD) {
        add(new Comment(data));
    } else if (data->type == NEBTYPE_COMMENT_DELETE) {
        Comment comment(data);
        remove(&comment);
    }
}

void TableDownComm::addDowntime(nebstruct_downtime_data *data) {
    if (data->type == NEBTYPE_DOWNTIME_ADD ||
        data->type == NEBTYPE_DOWNTIME_LOAD) {
        add(new Downtime(data));
    } else if (data->type == NEBTYPE_DOWNTIME_DELETE) {
        Downtime downtime(data);
        remove(&downtime);
    }
}

void TableDownComm::add(DowntimeOrComment *data) {
    dc_key tmp_key = make_pair(data->_id, data->_service != nullptr);
    auto it = _entries.find(tmp_key);

    // might be update -> delete previous data set
    if (it != _entries.end()) {
        delete it->second;
        _entries.erase(it);
    }
    _entries.insert(make_pair(tmp_key, data));
}

void TableDownComm::remove(DowntimeOrComment *data) {
    dc_key tmp_key = make_pair(data->_id, data->_service != nullptr);
    auto it = _entries.find(tmp_key);
    if (it == _entries.end()) {
        logger(LG_INFO, "Cannot delete non-existing downtime/comment %lu",
               data->_id);
    } else {
        delete it->second;
        _entries.erase(it);
    }
}

void TableDownComm::answerQuery(Query *query) {
    for (const auto &entry : _entries) {
        if (!query->processDataset(entry.second)) {
            break;
        }
    }
}

bool TableDownComm::isAuthorized(contact *ctc, void *data) {
    DowntimeOrComment *dtc = static_cast<DowntimeOrComment *>(data);
    return is_authorized_for(ctc, dtc->_host, dtc->_service) != 0;
}

DowntimeOrComment *TableDownComm::findEntry(unsigned long id, bool is_service) {
    dc_key tmp_key = make_pair(id, is_service);
    auto it = _entries.find(tmp_key);
    if (it != _entries.end()) {
        return it->second;
    }
    return nullptr;
}
