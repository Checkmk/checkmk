// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DowntimeColumn_h
#define DowntimeColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <string>
#include <vector>

#include "ListColumn.h"
#include "contact_fwd.h"
class ColumnOffsets;
struct DowntimeData;
class MonitoringCore;
class Row;
class RowRenderer;

class DowntimeColumn : public ListColumn {
public:
    enum class info { none, medium, full };

    DowntimeColumn(const std::string &name, const std::string &description,
                   const ColumnOffsets &offsets, MonitoringCore *mc,
                   bool is_service, info with_info)
        : ListColumn(name, description, offsets)
        , _mc(mc)
        , _is_service(is_service)
        , _with_info(with_info) {}

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

private:
    MonitoringCore *_mc;
    bool _is_service;
    info _with_info;

    [[nodiscard]] std::vector<DowntimeData> downtimes_for_row(Row row) const;
};

#endif  // DowntimeColumn_h
