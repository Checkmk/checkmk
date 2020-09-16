// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "FileColumn.h"

#include <filesystem>
#include <sstream>
#include <utility>

#include "Logger.h"
#include "Row.h"

template <class T>
FileColumn<T>::FileColumn(
    const std::string& name, const std::string& description,
    const ColumnOffsets& offsets,
    std::function<std::filesystem::path()> basepath,
    std::function<std::filesystem::path(const T&)> filepath)
    : BlobColumn(name, description, offsets)
    , _basepath(std::move(basepath))
    , _filepath(std::move(filepath)) {}

template <class T>
std::unique_ptr<std::vector<char>> FileColumn<T>::getValue(Row row) const {
    auto path = _basepath();
    if (!std::filesystem::exists(path)) {
        // The basepath is not configured.
        return nullptr;
    }
    const T* data = columnData<T>(row);
    if (data == nullptr) {
        return nullptr;
    }
    auto filepath = _filepath(*data);
    if (!filepath.empty()) {
        path /= filepath;
    }
    if (!std::filesystem::is_regular_file(path)) {
        Warning(logger()) << path << " is not a regular file";
        return nullptr;
    }
    auto file_size = std::filesystem::file_size(path);
    std::ifstream ifs;
    ifs.open(path, std::ifstream::in | std::ifstream::binary);
    if (!ifs.is_open()) {
        generic_error ge("cannot open " + path.string());
        Warning(logger()) << ge;
        return nullptr;
    }
    using iterator = std::istreambuf_iterator<char>;
    auto buffer = std::make_unique<std::vector<char>>(file_size);
    buffer->assign(iterator{ifs}, iterator{});
    if (buffer->size() != file_size) {
        Warning(logger()) << "premature EOF reading " << path;
        return nullptr;
    }
    return buffer;
}
