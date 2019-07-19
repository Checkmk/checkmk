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

#include "pnp4nagios.h"
#include <cstddef>

#ifndef CMC
#include <filesystem>
#include <system_error>
#include "MonitoringCore.h"
#endif

namespace {

// TODO(sp): Move this to some kind of C++ string utility file.
std::string replace_all(const std::string& str, const std::string& chars,
                        char replacement) {
    std::string result(str);
    size_t i = 0;
    while ((i = result.find_first_of(chars, i)) != std::string::npos) {
        result[i++] = replacement;
    }
    return result;
}
}  // namespace

std::string pnp_cleanup(const std::string& name) {
    return replace_all(name, R"( /\:)", '_');
}

#ifndef CMC
// TODO(sp) Merge this with Perfdatabase::getPNPXMLPath
int pnpgraph_present(MonitoringCore* mc, const std::string& host,
                     const std::string& service) {
    std::filesystem::path pnp_path = mc->pnpPath();
    if (pnp_path.empty()) {
        return -1;
    }
    std::filesystem::path path =
        pnp_path / pnp_cleanup(host) / (pnp_cleanup(service) + ".xml");
    std::error_code ec;
    std::filesystem::status(path, ec);
    return ec ? 0 : 1;
}
#endif
