// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DynamicFileColumn_h
#define DynamicFileColumn_h

#include "config.h"  // IWYU pragma: keep

#include <filesystem>
#include <functional>
#include <memory>
#include <string>

#include "Column.h"
#include "DynamicColumn.h"

template <class T>
class DynamicFileColumn : public DynamicColumn {
public:
    DynamicFileColumn(
        const std::string &name, const std::string &description,
        const ColumnOffsets &, std::function<std::filesystem::path()> basepath,
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

#endif  // DynamicFileColumn_h
