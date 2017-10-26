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

#include "DowntimeColumn.h"
#include "MonitoringCore.h"
#include "Renderer.h"
#include "Row.h"

#ifndef CMC
#include "nagios.h"
#endif

void DowntimeColumn::output(Row row, RowRenderer &r,
                            const contact * /* auth_user */) const {
    ListRenderer l(r);
    for (const auto &downtime : downtimes_for_row(row)) {
        if (_with_info) {
            SublistRenderer s(l);
            s.output(downtime._id);
            s.output(downtime._author);
            s.output(downtime._comment);
        } else {
            l.output(downtime._id);
        }
    }
}

std::vector<std::string> DowntimeColumn::getValue(
    Row row, const contact * /*auth_user*/) const {
    std::vector<std::string> ids;
    for (const auto &downtime : downtimes_for_row(row)) {
        ids.push_back(std::to_string(downtime._id));
    }
    return ids;
}

std::vector<DowntimeData> DowntimeColumn::downtimes_for_row(Row row) const {
    if (auto data = columnData<void>(row)) {
        return _is_service
                   ? _mc->downtimes_for_service(
                         reinterpret_cast<const MonitoringCore::Service *>(
                             data))
                   : _mc->downtimes_for_host(
                         reinterpret_cast<const MonitoringCore::Host *>(data));
    }
    return {};
}
