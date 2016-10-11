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
#include <cstdio>
#include <ostream>
#include "Logger.h"
#include "pnp4nagios.h"

using std::string;

string mk_logwatch_path_of_host(const string &host_name) {
    string path(MK_LOGWATCH_PATH);
    if (path == "") {
        return "";
    }
    path += pnp_cleanup(host_name);
    return path;
}

void mk_logwatch_acknowledge(const string &host_name, const string &file_name) {
    Logger *logger = Logger::getLogger("cmk.livestatus");
    if (file_name.find('/') != string::npos) {
        Warning(logger) << "Invalid character / in mk_logfile filename '"
                        << file_name << "' of host '" << host_name << "'";
        return;
    }

    string path(MK_LOGWATCH_PATH);
    if (path == "") {
        return;
    }
    path += pnp_cleanup(host_name) + "/" + file_name;

    int r = remove(path.c_str());
    if (r != 0) {
        Warning(logger) << generic_error(
            "Cannot acknowledge mk_logfile file '" + file_name + "' of host '" +
            host_name + "'");
    }
}
