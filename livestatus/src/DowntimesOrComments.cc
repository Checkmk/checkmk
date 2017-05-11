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

#include "DowntimesOrComments.h"
#include <iosfwd>
#include "DowntimeOrComment.h"
#include "Logger.h"

using std::make_unique;

DowntimesOrComments::DowntimesOrComments()
    : _logger(Logger::getLogger("cmk.livestatus")) {}

void DowntimesOrComments::registerDowntime(nebstruct_downtime_data *data) {
    unsigned long id = data->downtime_id;
    switch (data->type) {
        case NEBTYPE_DOWNTIME_ADD:
        case NEBTYPE_DOWNTIME_LOAD:
            _entries[id] = make_unique<Downtime>(data);
            break;
        case NEBTYPE_DOWNTIME_DELETE:
            if (_entries.erase(id) == 0) {
                Informational(_logger)
                    << "Cannot delete non-existing downtime " << id;
            }
            break;
        default:
            break;
    }
}

void DowntimesOrComments::registerComment(nebstruct_comment_data *data) {
    unsigned long id = data->comment_id;
    switch (data->type) {
        case NEBTYPE_COMMENT_ADD:
        case NEBTYPE_COMMENT_LOAD:
            _entries[id] = make_unique<Comment>(data);
            break;
        case NEBTYPE_COMMENT_DELETE:
            if (_entries.erase(id) == 0) {
                Informational(_logger)
                    << "Cannot delete non-existing comment " << id;
            }
            break;
        default:
            break;
    }
}
