// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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
#include "TableHosts.h"
#include "TableServices.h"
#include "DowntimeOrComment.h"
#include "logger.h"
#include "Query.h"
#include "OffsetStringColumn.h"
#include "OffsetIntColumn.h"
#include "OffsetTimeColumn.h"
#include "auth.h"
#include "tables.h"

// Todo: the dynamic data in this table must be
// locked with a mutex

TableDownComm::TableDownComm(bool is_downtime)
{
    if (is_downtime)
        _name = "downtimes";
    else
        _name = "comments";

    DowntimeOrComment *ref = 0;
    addColumn(new OffsetStringColumn("author",
                is_downtime ? "The contact that scheduled the downtime" : "The contact that entered the comment",
                (char *)&(ref->_author_name) - (char *)ref));
    addColumn(new OffsetStringColumn("comment",
                "A comment text", (char *)&(ref->_comment) - (char *)ref));
    addColumn(new OffsetIntColumn("id",
                is_downtime ? "The id of the downtime" : "The id of the comment", (char *)&(ref->_id) - (char *)ref));
    addColumn(new OffsetTimeColumn("entry_time",
                "The time the entry was made as UNIX timestamp", (char *)&(ref->_entry_time) - (char *)ref));
    addColumn(new OffsetIntColumn("type",
                is_downtime ?  "The type of the downtime: 0 if it is active, 1 if it is pending" :
                "The type of the comment: 1 is host, 2 is service", (char *)&(ref->_type) - (char *)ref));
    addColumn(new OffsetIntColumn("is_service",
                "0, if this entry is for a host, 1 if it is for a service", (char *)&(ref->_is_service) - (char *)ref));

    if (is_downtime)
    {
        Downtime *ref = 0;
        addColumn(new OffsetTimeColumn("start_time",
                    "The start time of the downtime as UNIX timestamp", (char *)&(ref->_start_time) - (char *)ref));
        addColumn(new OffsetTimeColumn("end_time",
                    "The end time of the downtime as UNIX timestamp", (char *)&(ref->_end_time) - (char *)ref));
        addColumn(new OffsetIntColumn("fixed",
                    "A 1 if the downtime is fixed, a 0 if it is flexible", (char *)&(ref->_fixed) - (char *)ref));
        addColumn(new OffsetIntColumn("duration",
                    "The duration of the downtime in seconds", (char *)&(ref->_duration) - (char *)ref));
        addColumn(new OffsetIntColumn("triggered_by",
                    "The id of the downtime this downtime was triggered by or 0 if it was not triggered by another downtime",
                    (char *)&(ref->_triggered_by) - (char *)ref));
    }
    else {
        Comment *ref = 0;
        addColumn(new OffsetIntColumn("persistent",
                    "Whether this comment is persistent (0/1)", (char *)&(ref->_persistent) - (char *)ref));
        addColumn(new OffsetIntColumn("source",
                    "The source of the comment (0 is internal and 1 is external)", (char *)&(ref->_persistent) - (char *)ref));
        addColumn(new OffsetIntColumn("entry_type",
                    "The type of the comment: 1 is user, 2 is downtime, 3 is flap and 4 is acknowledgement", (char *)&(ref->_entry_type) - (char *)ref));
        addColumn(new OffsetIntColumn("expires",
                    "Whether this comment expires", (char *)&(ref->_expires) - (char *)ref));
        addColumn(new OffsetTimeColumn("expire_time",
                    "The time of expiry of this comment as a UNIX timestamp", (char *)&(ref->_expire_time) - (char *)ref));
    }

    g_table_hosts->addColumns(this, "host_",    (char *)&(ref->_host)    - (char *)ref);
    g_table_services->addColumns(this, "service_", (char *)&(ref->_service) - (char *)ref, false /* no hosts table */);
}

TableDownComm::~TableDownComm()
{
    for (_entries_t::iterator it = _entries.begin();
            it != _entries.end();
            ++it)
    {
        delete it->second;
    }
}

void TableDownComm::addComment(nebstruct_comment_data *data) {
    unsigned long id = data->comment_id;
    if (data->type == NEBTYPE_COMMENT_ADD || data->type == NEBTYPE_COMMENT_LOAD) {
        add(new Comment(data));
    }
    else if (data->type == NEBTYPE_COMMENT_DELETE) {
        remove(id);
    }
}


void TableDownComm::addDowntime(nebstruct_downtime_data *data)
{
    unsigned long id = data->downtime_id;
    if (data->type == NEBTYPE_DOWNTIME_ADD || data->type == NEBTYPE_DOWNTIME_LOAD) {
        add(new Downtime(data));
    }
    else if (data->type == NEBTYPE_DOWNTIME_DELETE) {
        remove(id);
    }
}


void TableDownComm::add(DowntimeOrComment *data)
{
    _entries_t::iterator it = _entries.find(data->_id);
    // might be update -> delete previous data set
    if (it != _entries.end()) {
        delete it->second;
        _entries.erase(it);
    }
    _entries.insert(make_pair(data->_id, data));
}

void TableDownComm::remove(unsigned id)
{
    _entries_t::iterator it = _entries.find(id);
    if (it == _entries.end())
        logger(LG_INFO, "Cannot delete non-existing downtime/comment %u", id);
    else {
        delete it->second;
        _entries.erase(it);
    }
}

void TableDownComm::answerQuery(Query *query)
{
    for (_entries_t::const_iterator it = _entries.begin();
            it != _entries.end();
            ++it)
    {
        if (!query->processDataset(it->second))
            break;
    }
}

bool TableDownComm::isAuthorized(contact *ctc, void *data)
{
    DowntimeOrComment *dtc = (DowntimeOrComment *)data;
    return is_authorized_for(ctc, dtc->_host, dtc->_service);
}

DowntimeOrComment *TableDownComm::findEntry(unsigned long id)
{
    _entries_t::iterator it = _entries.find(id);
    if (it != _entries.end())
        return it->second;
    else
        return 0;
}


