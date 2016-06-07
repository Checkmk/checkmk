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

#include "DownCommColumn.h"
#include <stdint.h>
#include <stdlib.h>
#include <memory>
#include <utility>
#include "DowntimeOrComment.h"
#include "DowntimesOrComments.h"
#include "Query.h"
#include "nagios.h"

void DownCommColumn::output(void *data, Query *query) {
    query->outputBeginList();
    data = shiftPointer(data);  // points to host or service
    if (data != nullptr) {
        bool first = true;
        for (const auto &entry : _holder) {
            unsigned long id = entry.first;
            DowntimeOrComment *dt = entry.second.get();
            if (match(dt, data)) {
                if (first) {
                    first = false;
                } else {
                    query->outputListSeparator();
                }
                if (_with_info) {
                    query->outputBeginSublist();
                    query->outputUnsignedLong(id);
                    query->outputSublistSeparator();
                    query->outputString(dt->_author_name);
                    query->outputSublistSeparator();
                    query->outputString(dt->_comment);
                    if (_with_extra_info && !_is_downtime) {
                        query->outputSublistSeparator();
                        query->outputInteger(
                            static_cast<Comment *>(dt)->_entry_type);
                        query->outputSublistSeparator();
                        query->outputTime(dt->_entry_time);
                    }
                    query->outputEndSublist();
                } else {
                    query->outputUnsignedLong(id);
                }
            }
        }
    }
    query->outputEndList();
}

bool DownCommColumn::match(DowntimeOrComment *dt, void *data) {
    // TableDownComm always enumerates dowtimes/comments for both hosts and
    // services, regardless of what we are interested in. So we have to skip the
    // ones which have the wrong kind.
    if (_is_service != (dt->_is_service != 0)) {
        return false;
    }

    if (_is_service) {
        service *s = static_cast<service *>(data);
        return dt->_service != nullptr &&  // just to be sure...
               dt->_service->host_name == s->host_name &&
               dt->_service->description == s->description;
    }
    host *h = static_cast<host *>(data);
    return dt->_host->name == h->name;
}

void *DownCommColumn::getNagiosObject(char *name) {
    // Hack. Convert number into pointer.
    return static_cast<char *>(nullptr) + strtoul(name, nullptr, 10);
}

bool DownCommColumn::isNagiosMember(void *data, void *member) {
    // data points to a host or service
    // member is not a pointer, but an unsigned int (hack)
    unsigned long id = static_cast<unsigned long>(
        reinterpret_cast<uintptr_t>(member));  // Hack. Convert it back.
    DowntimeOrComment *dt = _holder.findEntry(id);
    return dt != nullptr && (dt->_service == static_cast<service *>(data) ||
                             (dt->_service == nullptr &&
                              dt->_host == static_cast<host *>(data)));
}

bool DownCommColumn::isEmpty(void *data) {
    if (data == nullptr) {
        return true;
    }

    for (const auto &entry : _holder) {
        DowntimeOrComment *dt = entry.second.get();
        if (dt->_service == data ||
            (dt->_service == nullptr && dt->_host == data)) {
            return false;
        }
    }
    return true;  // empty
}
