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

#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <unistd.h>

#include "pnp4nagios.h"


extern char *g_pnp_path;

char *cleanup_pnpname(char *name)
{
    char *p = name;
    while (*p) {
        if (*p == ' ' || *p == '/' || *p == '\\' || *p == ':')
            *p = '_';
        p++;
    }
    return name;
}


int pnpgraph_present(const char *host, const char *service)
{
    if (!g_pnp_path[0])
        return -1;

    char path[4096];
    size_t needed_size = strlen(g_pnp_path) + strlen(host) + 16;
    if (service)
        needed_size += strlen(service);
    if (needed_size > sizeof(path))
        return -1;

    strcpy(path, g_pnp_path);
    char *end = path + strlen(path);
    strcpy(end, host);
    cleanup_pnpname(end);
    strcat(end, "/");
    end = end + strlen(end);
    if (service) {
        strcat(end, service);
        cleanup_pnpname(end);
        strcat(end, ".xml");
    }
    else
        strcat(end, "_HOST_.xml");

    if (0 == access(path, R_OK))
        return 1;
    else
        return 0;
}


// Determines if a RRD database is existent and returns its path name.
// Returns an empty string otherwise.
// This assumes paths created in the PNP4Nagios style with storage type MULTIPLE.
string rrd_path(const char *host, const char *service, const char *varname)
{
    if (!g_pnp_path[0])
        return "";

    string path = g_pnp_path;
    path += "/";

    char *cleaned_up;
    cleaned_up = cleanup_pnpname(strdup(host));
    path += cleaned_up;
    free(cleaned_up);

    path += "/";

    cleaned_up = cleanup_pnpname(strdup(service));
    path += cleaned_up;
    free(cleaned_up);

    path += "_";

    cleaned_up = cleanup_pnpname(strdup(varname));
    path += cleaned_up;
    free(cleaned_up);

    path += ".rrd";

    struct stat st;
    if (0 == stat(path.c_str(), &st))
        return path;
    else
        return "";
}
