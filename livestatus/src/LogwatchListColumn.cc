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
#include <dirent.h>
#include "Renderer.h"
#include "pnp4nagios.h"

#ifdef CMC
#include "Host.h"
#endif

using std::string;

void LogwatchListColumn::output(void *row, RowRenderer &r,
                                contact * /* auth_user */) {
    void *data = shiftPointer(row);
    if (data == nullptr) {
        return;
    }

#ifdef CMC
    Host *host = static_cast<Host *>(data);
    string host_name = host->_name;
#else
    host *hst = static_cast<host *>(data);
    string host_name = hst->name;
#endif

    ListRenderer l(r);
    if (_logwatch_path.empty()) {
        return;
    }
    string path = _logwatch_path + pnp_cleanup(host_name);
    if (DIR *dir = opendir(path.c_str())) {
        while (true) {
            struct dirent de;
            struct dirent *dep;
            readdir_r(dir, &de, &dep);
            if (dep == nullptr) {
                closedir(dir);
                break;
            }
            string name = dep->d_name;
            if (name != "." && name != "..") {
                l.output(name);
            }
        }
    }
}
