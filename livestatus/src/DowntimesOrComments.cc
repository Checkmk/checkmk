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

#include "DowntimesOrComments.h"
#include <utility>
#include "DowntimeOrComment.h"
#include "logger.h"

DowntimesOrComments::~DowntimesOrComments() {
    for (auto &entry : _entries) {
        delete entry.second;
    }
}

void DowntimesOrComments::registerDowntime(nebstruct_downtime_data *data) {
    switch (data->type) {
        case NEBTYPE_DOWNTIME_ADD:
        case NEBTYPE_DOWNTIME_LOAD:
            add(new Downtime(data));
            break;
        case NEBTYPE_DOWNTIME_DELETE:
            remove(data->downtime_id);
            break;
        default:
            break;
    }
}

void DowntimesOrComments::registerComment(nebstruct_comment_data *data) {
    switch (data->type) {
        case NEBTYPE_COMMENT_ADD:
        case NEBTYPE_COMMENT_LOAD:
            add(new Comment(data));
            break;
        case NEBTYPE_COMMENT_DELETE:
            remove(data->comment_id);
            break;
        default:
            break;
    }
}

void DowntimesOrComments::add(DowntimeOrComment *data) {
    auto it = _entries.find(data->_id);
    if (it == _entries.end()) {
        _entries.emplace(data->_id, data);
    } else {
        delete it->second;
        it->second = data;
    }
}

void DowntimesOrComments::remove(unsigned long id) {
    auto it = _entries.find(id);
    if (it == _entries.end()) {
        logger(LG_INFO, "Cannot delete non-existing downtime/comment %lu", id);
    } else {
        delete it->second;
        _entries.erase(it);
    }
}

DowntimeOrComment *DowntimesOrComments::findEntry(unsigned long id) const {
    auto it = _entries.find(id);
    return it == _entries.end() ? nullptr : it->second;
}
