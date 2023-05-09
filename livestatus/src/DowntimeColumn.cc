// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DowntimeColumn.h"

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
    for (const auto &downtime : downtimes_for_row(row)) {
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

std::vector<std::string> DowntimeColumn::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    std::vector<std::string> ids;
    for (const auto &downtime : downtimes_for_row(row)) {
        ids.push_back(std::to_string(downtime._id));
    }
    return ids;
}

std::vector<DowntimeData> DowntimeColumn::downtimes_for_row(Row row) const {
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
