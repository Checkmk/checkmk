// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef HostFileColumn_h
#define HostFileColumn_h

#include "config.h"  // IWYU pragma: keep
#include <filesystem>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>
#include "BlobColumn.h"
#include "Column.h"
class Row;

class HostFileColumn : public BlobColumn {
public:
    HostFileColumn(const std::string& name, const std::string& description,
                   const Column::Offsets&,
                   std::function<std::filesystem::path()> basepath,
                   std::function<std::optional<std::filesystem::path>(
                       const Column&, const Row&)>
                       filepath);

    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row row) const override;
    [[nodiscard]] std::filesystem::path basepath() const;
    [[nodiscard]] std::optional<std::filesystem::path> filepath(
        const Row&) const;
    [[nodiscard]] std::optional<std::filesystem::path> abspath(
        const Row&) const;

private:
    const std::function<std::filesystem::path()> _basepath;
    const std::function<std::optional<std::filesystem::path>(const Column&,
                                                             const Row&)>
        _filepath;
};

#endif  // HostFileColumn_h
