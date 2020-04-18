// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DynamicColumn_h
#define DynamicColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include <string>
#include "Column.h"
class Logger;

class DynamicColumn {
public:
    DynamicColumn(std::string name, std::string description,
                  Column::Offsets offsets);
    virtual ~DynamicColumn();
    [[nodiscard]] std::string name() const;
    virtual std::unique_ptr<Column> createColumn(
        const std::string &name, const std::string &arguments) = 0;
    [[nodiscard]] Logger *logger() const;

protected:
    Logger *const _logger;
    const std::string _name;
    const std::string _description;  // Note: Currently unused!
    Column::Offsets _offsets;
};

#endif  // DynamicColumn_h
