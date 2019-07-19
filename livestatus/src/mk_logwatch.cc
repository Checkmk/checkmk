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

#include "mk_logwatch.h"
#include <ostream>
#include <system_error>
#include "Logger.h"
#include "pnp4nagios.h"

void mk_logwatch_acknowledge(Logger *logger,
                             const std::filesystem::path &logwatch_path,
                             const std::string &host_name,
                             const std::string &file_name) {
    if (file_name.find('/') != std::string::npos) {
        Warning(logger) << "Invalid character / in mk_logfile filename '"
                        << file_name << "' of host '" << host_name << "'";
        return;
    }
    if (logwatch_path.empty()) {
        return;
    }
    auto path = std::filesystem::path(logwatch_path) / pnp_cleanup(host_name) /
                file_name;
    std::error_code ec;
    if (!std::filesystem::remove(path, ec)) {
        generic_error ge("Cannot acknowledge mk_logfile file '" + file_name +
                         "' of host '" + host_name + "'");
        Warning(logger) << ge;
    }
}
