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

#include "LogwatchListColumn.h"
#include <algorithm>
#include <filesystem>
#include <iterator>
#include <ostream>
#include "Logger.h"
#include "MonitoringCore.h"
#include "Row.h"
#include "pnp4nagios.h"

#ifdef CMC
#include "Host.h"
#include "cmc.h"
#else
#include "nagios.h"
#endif

std::vector<std::string> LogwatchListColumn::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    auto dir = getDirectory(row);
    if (dir.empty()) {
        return {};
    }
    try {
        if (std::filesystem::exists(dir)) {
            std::vector<std::string> filenames;
            auto it = std::filesystem::directory_iterator(dir);
            std::transform(begin(it), end(it), std::back_inserter(filenames),
                           [](const auto &entry) {
                               return entry.path().filename().string();
                           });
            return filenames;
        }
    } catch (const std::filesystem::filesystem_error &e) {
        Warning(logger()) << name() << ": " << e.what();
    }
    return {};
}

std::filesystem::path LogwatchListColumn::getDirectory(Row row) const {
    auto logwatch_path = _mc->mkLogwatchPath();
    auto host_name = getHostName(row);
    return logwatch_path.empty() || host_name.empty()
               ? std::filesystem::path()
               : std::filesystem::path(logwatch_path) / pnp_cleanup(host_name);
}

std::string LogwatchListColumn::getHostName(Row row) const {
#ifdef CMC
    if (auto hst = columnData<Host>(row)) {
        return hst->name();
    }
#else
    if (auto hst = columnData<host>(row)) {
        return hst->name;
    }
#endif
    return "";
}
