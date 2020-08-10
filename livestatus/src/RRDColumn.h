// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDColumn_h
#define RRDColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <filesystem>
#include <functional>
#include <string>
#include <vector>

#include "Column.h"
#include "DynamicRRDColumn.h"
#include "ListColumn.h"
#include "Metric.h"
#include "contact_fwd.h"
class Logger;
class MonitoringCore;
class Row;
class RowRenderer;

class RRDColumn : public ListColumn {
public:
    RRDColumn(const std::string &name, const std::string &description,
              const Column::Offsets &, MonitoringCore *mc, RRDColumnArgs args);

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    std::vector<std::string> getValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const override;

    // HACK
    struct ObjectPointer {
        enum class Kind { objects, services, hosts };
        const void *ptr;
        Kind kind;
    };

    using MetricLocator = std::function<MetricLocation(const Metric::Name &)>;

protected:
    struct Data {
        std::chrono::system_clock::time_point start;
        std::chrono::system_clock::time_point end;
        unsigned long step{};
        std::vector<double> values;
    };

    static Data getData(Logger *logger,
                        const std::filesystem::path &rrdcached_socket_path,
                        const RRDColumnArgs &args,
                        const MetricLocator &locator);

    MonitoringCore *_mc;
    RRDColumnArgs _args;

private:
    [[nodiscard]] virtual Data getDataFor(Row row) const = 0;
};

#endif  // RRDColumn_h
