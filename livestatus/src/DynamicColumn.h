// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DynamicColumn_h
#define DynamicColumn_h

#include "config.h"  // IWYU pragma: keep

#include <memory>
#include <string>
#include <utility>

#include "Column.h"

class DynamicColumn {
public:
    DynamicColumn(std::string name, std::string description,
                  ColumnOffsets offsets)
        : _name(std::move(name))
        , _description(std::move(description))
        , _offsets(std::move(offsets)) {}
    virtual ~DynamicColumn() = default;

    [[nodiscard]] std::string name() const { return _name; };

    virtual std::unique_ptr<Column> createColumn(
        const std::string &name, const std::string &arguments) = 0;

protected:
    const std::string _name;
    const std::string _description;  // Note: Currently unused!
    ColumnOffsets _offsets;
};

#endif  // DynamicColumn_h
