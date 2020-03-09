// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostMetricsColumn.h"
#include <algorithm>
#include <filesystem>
#include <iterator>
#include <string>
#include <vector>
#include "Metric.h"
#include "MonitoringCore.h"
#include "Row.h"
#include "nagios.h"
#include "pnp4nagios.h"

HostMetricsColumn::HostMetricsColumn(const std::string& name,
                                     const std::string& description,
                                     const Column::Offsets& offsets,
                                     MonitoringCore* mc)
    : MetricsColumn(name, description, offsets)

    , _mc(mc) {}

std::vector<std::string> HostMetricsColumn::getValue(
    Row row, const contact* /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    auto* hst = columnData<host>(row);
    if (hst == nullptr || hst->name == nullptr) {
        return {};
    }
    Metric::Names names;
    scan_rrd(_mc->pnpPath() / hst->name, dummy_service_description(), names,
             _mc->loggerRRD());
    std::vector<std::string> result{names.size()};
    std::transform(std::begin(names), std::end(names), std::begin(result),
                   [](auto&& m) { return m.string(); });
    return result;
}
