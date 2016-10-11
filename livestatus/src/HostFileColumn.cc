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

#ifdef CMC
#include "Host.h"
#else
#include "nagios.h"
#endif

using std::make_unique;
using std::string;
using std::unique_ptr;
using std::vector;

HostFileColumn::HostFileColumn(string name, string description,
                               std::string base_dir, std::string suffix,
                               int indirect_offset, int extra_offset)
    : BlobColumn(name, description, indirect_offset, extra_offset)
    , _base_dir(move(base_dir))
    , _suffix(move(suffix)) {}

unique_ptr<vector<char>> HostFileColumn::getBlob(void *data) {
    if (_base_dir.empty()) {
        return nullptr;  // Path is not configured
    }

    data = shiftPointer(data);
    if (data == nullptr) {
        return nullptr;
    }

#ifdef CMC
    string host_name = static_cast<Host *>(data)->_name;
#else
    string host_name = static_cast<host *>(data)->name;
#endif

    string path = _base_dir + "/" + host_name + _suffix;
    int fd = open(path.c_str(), O_RDONLY);
    if (fd == -1) {
        // It is OK when inventory/logwatch files do not exist.
        if (errno != ENOENT) {
            Warning(_logger) << generic_error("cannot open " + path);
        }
        return nullptr;
    }

    struct stat st;
    if (fstat(fd, &st) == -1) {
        Warning(_logger) << generic_error("cannot stat " + path);
        return nullptr;
    }
    if (!S_ISREG(st.st_mode)) {
        Warning(_logger) << path << " is not a regular file";
        return nullptr;
    }

    size_t bytes_to_read = st.st_size;
    unique_ptr<vector<char>> result = make_unique<vector<char>>(bytes_to_read);
    char *buffer = &(*result)[0];
    while (bytes_to_read > 0) {
        ssize_t bytes_read = read(fd, buffer, bytes_to_read);
        if (bytes_read == -1) {
            if (errno != EINTR) {
                Warning(_logger) << generic_error("could not read " + path);
                close(fd);
                return nullptr;
            }
        } else if (bytes_read == 0) {
            Warning(_logger) << "premature EOF reading " << path;
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
