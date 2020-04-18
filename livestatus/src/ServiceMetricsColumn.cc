// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceMetricsColumn.h"
#include <algorithm>
#include <filesystem>
#include <iterator>
#include "Metric.h"
#include "MonitoringCore.h"
#include "Row.h"
#include "nagios.h"

ServiceMetricsColumn::ServiceMetricsColumn(const std::string& name,
                                           const std::string& description,
                                           const Column::Offsets& offsets,
                                           MonitoringCore* mc)
    : MetricsColumn(name, description, offsets), _mc(mc) {}

std::vector<std::string> ServiceMetricsColumn::getValue(
    Row row, const contact* /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    auto* svc = columnData<service>(row);
    if (svc == nullptr || svc->host_name == nullptr ||
        svc->description == nullptr) {
        return {};
    }
    Metric::Names names;
    scan_rrd(_mc->pnpPath() / svc->host_name, svc->description, names,
             _mc->loggerRRD());
    std::vector<std::string> result{names.size()};
    std::transform(std::begin(names), std::end(names), std::begin(result),
                   [](auto&& m) { return m.string(); });
    return result;
}
