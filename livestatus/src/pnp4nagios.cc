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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>

#include "pnp4nagios.h"

// Note: If the path is not empty, it always ends with '/', see
// livestatus_parse_arguments.
extern char* g_pnp_path;

namespace {

std::string replace_all(const std::string& str, const std::string& chars, char replacement) {
    std::string result(str);
    size_t i = 0;
    while ((i = result.find_first_of(chars, i)) != std::string::npos) {
        result[i++] = replacement;
    }
    return result;
}


std::string cleanup(const std::string& name) { return replace_all(name, " /\\:", '_'); }

}  // namespace


int pnpgraph_present(const std::string& host, const std::string& service) {
    std::string pnp_path(g_pnp_path);
    if (pnp_path.empty()) return -1;
    std::string path(pnp_path.append(cleanup(host))
                         .append("/")
                         .append(cleanup(service))
                         .append(".xml"));
    return access(path.c_str(), R_OK) == 0 ? 1 : 0;
}


std::string rrd_path(const std::string& host, const std::string& service,
                     const std::string& varname) {
    std::string pnp_path(g_pnp_path);
    if (pnp_path.empty()) return "";
    std::string path(pnp_path.append("/")
                         .append(cleanup(host))
                         .append("/")
                         .append(cleanup(service))
                         .append("_")
                         .append(cleanup(varname))
                         .append(".rrd"));
    struct stat st;
    return stat(path.c_str(), &st) == 0 ? path : "";
}
