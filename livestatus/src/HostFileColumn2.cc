// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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

#include "HostFileColumn2.h"
#include <filesystem>
#include <sstream>
#include <utility>
#include "Logger.h"
#include "Row.h"

// TODO(ml): This is a generalization of HostFileColumn.
//           The main difference is that the path where the file
//           is located is entirely the business of the caller.
//           This contrasts with HostFileColumn where the path
//           must contain the host name.
HostFileColumn2::HostFileColumn2(const std::string& name,
                                 const std::string& description,
                                 int indirect_offset, int extra_offset,
                                 int extra_extra_offset, int offset,
                                 std::filesystem::path basepath,
                                 std::filesystem::path filepath)
    : BlobColumn(name, description, indirect_offset, extra_offset,
                 extra_extra_offset, offset)
    , _basepath(std::move(basepath))
    , _relpath(std::move(filepath)) {}

[[nodiscard]] std::filesystem::path HostFileColumn2::basepath() const {
    return _basepath;
}
[[nodiscard]] std::filesystem::path HostFileColumn2::relpath() const {
    return _relpath;
}
[[nodiscard]] std::filesystem::path HostFileColumn2::abspath() const {
    return _basepath / _relpath;
}

std::unique_ptr<std::vector<char>> HostFileColumn2::getValue(Row row) const {
    (void)row;  // Silence `unused parameter` warning.
    if (!std::filesystem::exists(basepath())) {
        // The basepath is not configured.
        return nullptr;
    }
    if (!std::filesystem::is_regular_file(abspath())) {
        Warning(logger()) << abspath() << " is not a regular file";
        return nullptr;
    }
    auto file_size = std::filesystem::file_size(abspath());
    if (file_size == 0) {
        // The file is empty: there is nothing more to do.
        return nullptr;
    }
    std::ifstream ifs;
    ifs.open(abspath(), std::ifstream::in | std::ifstream::binary);
    if (!ifs.is_open()) {
        generic_error ge("cannot open " + abspath().string());
        Warning(logger()) << ge;
        return nullptr;
    }
    using iterator = std::istreambuf_iterator<char>;
    auto buffer = std::make_unique<std::vector<char>>(file_size);
    buffer->assign(iterator{ifs}, iterator{});
    if (buffer->size() != file_size) {
        Warning(logger()) << "premature EOF reading " << abspath();
        return nullptr;
    }
    return buffer;
}
