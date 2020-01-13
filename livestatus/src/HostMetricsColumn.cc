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
