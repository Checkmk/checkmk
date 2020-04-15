// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDColumn_h
#define RRDColumn_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <ctime>
#include <string>
#include <vector>
#include "Column.h"
#include "ListColumn.h"
#include "contact_fwd.h"
class MonitoringCore;
class Row;
class RowRenderer;

class RRDColumn : public ListColumn {
public:
    RRDColumn(const std::string &name, const std::string &description,
              const Column::Offsets &, MonitoringCore *mc, std::string rpn,
              time_t start_time, time_t end_time, int resolution,
              int max_entries);

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

    enum class Table { objects, services, hosts };

private:
    [[nodiscard]] virtual const void *getObject(Row row) const = 0;
    [[nodiscard]] virtual Table table() const = 0;

    MonitoringCore *_mc;
    std::string _rpn;
    time_t _start_time;
    time_t _end_time;
    int _resolution;
    int _max_entries;

    struct Data {
        std::chrono::system_clock::time_point start;
        std::chrono::system_clock::time_point end;
        unsigned long step{};
        std::vector<double> values;
    };

    [[nodiscard]] Data getData(Row row) const;
};

#endif  // RRDColumn_h
