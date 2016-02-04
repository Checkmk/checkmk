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

#include "pnp4nagios.h"
#include <stddef.h>
#include <sys/stat.h>
#include <unistd.h>

using std::string;

// Note: If the path is not empty, it always ends with '/', see
// livestatus_parse_arguments.
extern char* g_pnp_path;

namespace {

// TODO(sp): Move this to some kind of C++ string utility file.
string replace_all(const string& str, const string& chars, char replacement) {
    string result(str);
    size_t i = 0;
    while ((i = result.find_first_of(chars, i)) != string::npos) {
        result[i++] = replacement;
    }
    return result;
}
}  // namespace

string pnp_cleanup(const string& name) {
    return replace_all(name, " /\\:", '_');
}

int pnpgraph_present(const string& host, const string& service) {
    string pnp_path(g_pnp_path);
    if (pnp_path.empty()) {
        return -1;
    }
    string path(pnp_path.append(pnp_cleanup(host))
                    .append("/")
                    .append(pnp_cleanup(service))
                    .append(".xml"));
    return access(path.c_str(), R_OK) == 0 ? 1 : 0;
}

string rrd_path(const string& host, const string& service,
                const string& varname) {
    string pnp_path(g_pnp_path);
    if (pnp_path.empty()) {
        return "";
    }
    string path(pnp_path.append("/")
                    .append(pnp_cleanup(host))
                    .append("/")
                    .append(pnp_cleanup(service))
                    .append("_")
                    .append(pnp_cleanup(varname))
                    .append(".rrd"));
    struct stat st;
    return stat(path.c_str(), &st) == 0 ? path : "";
}
