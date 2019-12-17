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

#include "HostFileColumn.h"
#include <filesystem>
#include <sstream>
#include <utility>
#include "Logger.h"
#include "Row.h"

HostFileColumn::HostFileColumn(
    const std::string& name, const std::string& description,
    const Column::Offsets& offsets,
    std::function<std::filesystem::path()> basepath,
    std::function<std::optional<std::filesystem::path>(const Column&,
                                                       const Row&)>
        filepath)
    : BlobColumn(name, description, offsets)
    , _basepath(std::move(basepath))
    , _filepath(std::move(filepath)) {}

[[nodiscard]] std::filesystem::path HostFileColumn::basepath() const {
    return _basepath();
}

[[nodiscard]] std::optional<std::filesystem::path> HostFileColumn::filepath(
    const Row& row) const {
    return _filepath(*this, row);
}

[[nodiscard]] std::optional<std::filesystem::path> HostFileColumn::abspath(
    const Row& row) const {
    if (auto f = filepath(row)) {
        return basepath() / *f;
    }
    return {};
}

std::unique_ptr<std::vector<char>> HostFileColumn::getValue(Row row) const {
    if (!std::filesystem::exists(basepath())) {
        // The basepath is not configured.
        return nullptr;
    }
    auto path = abspath(row);
    if (!path) {
        return nullptr;
    }
    if (!std::filesystem::is_regular_file(*path)) {
        Warning(logger()) << *path << " is not a regular file";
        return nullptr;
    }
    auto file_size = std::filesystem::file_size(*path);
    std::ifstream ifs;
    ifs.open(*path, std::ifstream::in | std::ifstream::binary);
    if (!ifs.is_open()) {
        generic_error ge("cannot open " + path->string());
        Warning(logger()) << ge;
        return nullptr;
    }
    using iterator = std::istreambuf_iterator<char>;
    auto buffer = std::make_unique<std::vector<char>>(file_size);
    buffer->assign(iterator{ifs}, iterator{});
    if (buffer->size() != file_size) {
        Warning(logger()) << "premature EOF reading " << *path;
        return nullptr;
    }
    return buffer;
}
