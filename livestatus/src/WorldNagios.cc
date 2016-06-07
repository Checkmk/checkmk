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

#include "WorldNagios.h"
#include <string.h>
#include "strutil.h"

service *getServiceBySpec(char *spec) {
    char *host_name;
    char *description;

    // The protocol proposes spaces as a separator between
    // the host name and the service description. That introduces
    // the problem that host name containing spaces will not work.
    // For that reason we alternatively allow a semicolon as a separator.
    char *semicolon = strchr(spec, ';');
    if (semicolon != nullptr) {
        *semicolon = 0;
        host_name = rstrip(spec);
        description = rstrip(semicolon + 1);
    } else {
        host_name = next_field(&spec);
        description = spec;
    }
    return find_service(host_name, description);
}
