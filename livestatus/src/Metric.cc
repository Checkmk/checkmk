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

#include "Metric.h"
#include <sstream>
#include "Logger.h"
#include "StringUtils.h"

void scan_rrd(const std::filesystem::path& basedir, const std::string& desc,
              Metric::Names& names, Logger* logger) {
    Informational(logger) << "scanning for metrics of " << desc << " in "
                          << basedir;
    std::string base = pnp_cleanup(desc + " ");
    try {
        for (const auto& entry : std::filesystem::directory_iterator(basedir)) {
            if (entry.path().extension() == ".rrd") {
                auto stem = entry.path().filename().stem().string();
                if (mk::starts_with(stem, base)) {
                    // NOTE: This is the main reason for mangling: The part of
                    // the file name after the stem is considered a mangled
                    // metric name.
                    names.emplace_back(stem.substr(base.size()));
                }
            }
        }
    } catch (const std::filesystem::filesystem_error& e) {
        if (e.code() == std::errc::no_such_file_or_directory) {
            Debug(logger) << "directory " << basedir << " does not exist yet";
        } else {
            Warning(logger) << "scanning directory for metrics: " << e.what();
        }
    }
}
