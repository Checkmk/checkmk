// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef FileColumn_h
#define FileColumn_h

#include "config.h"  // IWYU pragma: keep

#include <filesystem>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "BlobColumn.h"
#include "Column.h"
class Row;

template <class T>
class FileColumn : public BlobColumn {
public:
    FileColumn(const std::string& name, const std::string& description,
               const ColumnOffsets&,
               std::function<std::filesystem::path()> basepath,
               std::function<std::filesystem::path(const T&)> filepath);

    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row row) const override;

private:
    const std::function<std::filesystem::path()> _basepath;
    const std::function<std::filesystem::path(const T&)> _filepath;
};

#endif  // FileColumn_h
