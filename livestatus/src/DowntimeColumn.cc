// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DowntimeColumn.h"

#include <algorithm>
#include <iterator>

#include "MonitoringCore.h"
#include "Renderer.h"
#include "Row.h"

#ifndef CMC
#include "nagios.h"
#endif

void DowntimeColumn::output(Row row, RowRenderer &r,
                            const contact * /*auth_user*/,
                            std::chrono::seconds /*timezone_offset*/) const {
    ListRenderer l(r);
    for (const auto &downtime : getEntries(row)) {
        switch (_with_info) {
            case info::none:
                l.output(downtime._id);
                break;
            case info::medium: {
                SublistRenderer s(l);
                s.output(downtime._id);
                s.output(downtime._author);
                s.output(downtime._comment);
                break;
            }
            case info::full: {
                SublistRenderer s(l);
                s.output(downtime._id);
                s.output(downtime._author);
                s.output(downtime._comment);
                s.output(downtime._origin_is_rule);
                s.output(downtime._entry_time);
                s.output(downtime._start_time);
                s.output(downtime._end_time);
                s.output(downtime._fixed);
                s.output(std::chrono::duration_cast<std::chrono::seconds>(
                             downtime._duration)
                             .count());
                s.output(downtime._recurring);
                s.output(downtime._pending);
                break;
            }
        }
    }
}

/// \sa Apart from the lambda, the code is the same in
///    * CommentColumn::getValue()
///    * DowntimeColumn::getValue()
///    * ServiceGroupMembersColumn::getValue()
///    * ServiceListColumn::getValue()
std::vector<std::string> DowntimeColumn::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    auto entries = getEntries(row);
    std::vector<std::string> values;
    std::transform(entries.begin(), entries.end(), std::back_inserter(values),
                   [](const auto &entry) { return std::to_string(entry._id); });
    return values;
}

std::vector<DowntimeData> DowntimeColumn::getEntries(Row row) const {
    if (const auto *data = columnData<void>(row)) {
        return _is_service
                   ? _mc->downtimes_for_service(
                         reinterpret_cast<const MonitoringCore::Service *>(
                             data))
                   : _mc->downtimes_for_host(
                         reinterpret_cast<const MonitoringCore::Host *>(data));
    }
    return {};
}
