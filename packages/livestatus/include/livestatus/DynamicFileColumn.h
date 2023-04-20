// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DynamicFileColumn_h
#define DynamicFileColumn_h

#include <filesystem>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>

#include "livestatus/BlobColumn.h"
#include "livestatus/Column.h"
#include "livestatus/DynamicColumn.h"
#include "livestatus/FileSystemHelper.h"

template <class T>
class DynamicFileColumn : public DynamicColumn {
public:
    DynamicFileColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &offsets,
        std::function<std::filesystem::path()> basepath,
        std::function<std::filesystem::path(const T &, const std::string &args)>
            filepath);
    std::unique_ptr<Column> createColumn(const std::string &name,
                                         const std::string &arguments) override;
    [[nodiscard]] std::filesystem::path basepath() const;

private:
    const std::function<std::filesystem::path()> _basepath;
    const std::function<std::filesystem::path(const T &,
                                              const std::string &args)>
        _filepath;
};

template <class T>
DynamicFileColumn<T>::DynamicFileColumn(
    const std::string &name, const std::string &description,
    const ColumnOffsets &offsets,
    std::function<std::filesystem::path()> basepath,
    std::function<std::filesystem::path(const T &, const std::string &)>
        filepath)
    : DynamicColumn(name, description, offsets)
    , _basepath{std::move(basepath)}
    , _filepath{std::move(filepath)} {}

template <class T>
[[nodiscard]] std::filesystem::path DynamicFileColumn<T>::basepath() const {
    // This delays the call to mc to after it is constructed.
    return _basepath();
}

template <class T>
std::unique_ptr<Column> DynamicFileColumn<T>::createColumn(
    const std::string &name, const std::string &arguments) {
    // Arguments contains a path relative to basepath and possibly escaped.
    if (arguments.empty()) {
        throw std::runtime_error("invalid arguments for column '" + _name +
                                 "': missing file name");
    }
    const std::filesystem::path f{mk::unescape_filename(arguments)};
    if (!mk::path_contains(basepath(), basepath() / f)) {
        // Prevent malicious attempts to read files as root with
        // "/etc/shadow" (abs paths are not stacked) or
        // "../../../../etc/shadow".
        throw std::runtime_error("invalid arguments for column '" + _name +
                                 "': '" + f.string() + "' not in '" +
                                 basepath().string() + "'");
    }
    return std::make_unique<BlobColumn<T>>(
        name, _description, _offsets,
        BlobFileReader<T>{_basepath,
                          [this, f](const T &r) { return _filepath(r, f); }});
}

#endif  // DynamicFileColumn_h
