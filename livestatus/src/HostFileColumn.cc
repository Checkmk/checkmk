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

#include "HostFileColumn.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
#include <ostream>
#include <utility>
#include "Logger.h"
#include "Row.h"

#ifdef CMC
#include "Host.h"
#else
#include "nagios.h"
#endif

HostFileColumn::HostFileColumn(const std::string& name,
                               const std::string& description,
                               int indirect_offset, int extra_offset,
                               int extra_extra_offset, int offset,
                               std::string base_dir, std::string suffix)
    : BlobColumn(name, description, indirect_offset, extra_offset,
                 extra_extra_offset, offset)
    , _base_dir(std::move(base_dir))
    , _suffix(std::move(suffix)) {}

std::unique_ptr<std::vector<char>> HostFileColumn::getValue(Row row) const {
    if (_base_dir.empty()) {
        return nullptr;  // Path is not configured
    }

#ifdef CMC
    auto hst = columnData<Host>(row);
    if (hst == nullptr) {
        return nullptr;
    }
    std::string host_name = hst->name();
#else
    auto hst = columnData<host>(row);
    if (hst == nullptr) {
        return nullptr;
    }
    std::string host_name = hst->name;
#endif

    std::string path = _base_dir + "/" + host_name + _suffix;
    int fd = open(path.c_str(), O_RDONLY);
    if (fd == -1) {
        // It is OK when inventory/logwatch files do not exist.
        if (errno != ENOENT) {
            generic_error ge("cannot open " + path);
            Warning(logger()) << ge;
        }
        return nullptr;
    }

    struct stat st;
    if (fstat(fd, &st) == -1) {
        generic_error ge("cannot stat " + path);
        Warning(logger()) << ge;
        return nullptr;
    }
    if (!S_ISREG(st.st_mode)) {
        Warning(logger()) << path << " is not a regular file";
        return nullptr;
    }

    size_t bytes_to_read = st.st_size;
    auto result = std::make_unique<std::vector<char>>(bytes_to_read);
    char* buffer = &(*result)[0];
    while (bytes_to_read > 0) {
        ssize_t bytes_read = read(fd, buffer, bytes_to_read);
        if (bytes_read == -1) {
            if (errno != EINTR) {
                generic_error ge("could not read " + path);
                Warning(logger()) << ge;
                close(fd);
                return nullptr;
            }
        } else if (bytes_read == 0) {
            Warning(logger()) << "premature EOF reading " << path;
            close(fd);
            return nullptr;
        } else {
            bytes_to_read -= bytes_read;
            buffer += bytes_read;
        }
    }

    close(fd);
    return result;
}
