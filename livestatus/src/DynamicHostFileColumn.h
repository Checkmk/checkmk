// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DynamicHostFileColumn_h
#define DynamicHostFileColumn_h

#include "config.h"  // IWYU pragma: keep
#include <filesystem>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include "Column.h"
#include "DynamicColumn.h"
class Row;

class DynamicHostFileColumn : public DynamicColumn {
public:
    DynamicHostFileColumn(
        const std::string &name, const std::string &description,
        Column::Offsets, std::function<std::filesystem::path()> basepath,
        std::function<std::optional<std::filesystem::path>(
            const Column &, const Row &, const std::string &args)>
            filepath);
    std::unique_ptr<Column> createColumn(const std::string &name,
                                         const std::string &arguments) override;
    [[nodiscard]] std::filesystem::path basepath() const;

private:
    const std::function<std::filesystem::path()> _basepath;
    const std::function<std::optional<std::filesystem::path>(
        const Column &, const Row &, const std::string &args)>
        _filepath;
};

#endif  // DynamicHostFileColumn_h
