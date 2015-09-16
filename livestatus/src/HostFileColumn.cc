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


#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <nagios.h>

#include "logger.h"
#include "HostFileColumn.h"

#ifdef CMC
#include "Host.h"
#endif


HostFileColumn::HostFileColumn(string name, string description, const char *base_dir,
               const char *suffix, int indirect_offset)
    : BlobColumn(name, description, indirect_offset)
    , _base_dir(base_dir)
    , _suffix(suffix)
{
}

// returns a buffer to be freed afterwards!! Return 0
// in size of a missing file
char *HostFileColumn::getBlob(void *data, int *size)
{
    *size = 0;
    if (!_base_dir[0])
        return 0; // Path is not configured

    data = shiftPointer(data);
    if (!data) return 0;

#ifdef CMC
    Host *hst = (Host *)data;
    const char *host_name = hst->_name;
#else
    host *hst = (host *)data;
    const char *host_name = hst->name;
#endif

    char path[4096];
    snprintf(path, sizeof(path), "%s/%s%s", _base_dir.c_str(), host_name, _suffix.c_str());
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        return 0;
    }

    *size = lseek(fd, 0, SEEK_END);
    if (*size < 0) {
        close(fd);
        *size = 0;
        logger(LG_WARN, "Cannot seek to end of file %s", path);
        return 0;
    }

    lseek(fd, 0, SEEK_SET);
    char *buffer = (char *)malloc(*size);
    if (!buffer) {
        close(fd);
        return 0;
    }

    int read_bytes = read(fd, buffer, *size);
    close(fd);
    if (read_bytes != *size) {
        logger(LG_WARN, "Cannot read %d from %s", *size, path);
        free(buffer);
        return 0;
    }

    return buffer;
}
