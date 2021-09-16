// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Column.h"

#include <utility>

Column::Column(std::string name, std::string description, ColumnOffsets offsets)
    : _logger{"cmk.livestatus"}
    , _name(std::move(name))
    , _description(std::move(description))
    , _offsets(std::move(offsets)) {}

const void *Column::shiftPointer(Row row) const {
    return _offsets.shiftPointer(row);
}

ColumnOffsets ColumnOffsets::add(const shifter &shifter) const {
    ColumnOffsets result{*this};
    result.shifters_.emplace_back(shifter);
    return result;
}

const void *ColumnOffsets::shiftPointer(Row row) const {
    for (const auto &s : shifters_) {
        // TODO(sp) Figure out what is actually going on regarding nullptr...
        if (row.isNull()) {
            break;
        }
        row = Row{s(row)};
    }
    return row.rawData<void>();
}
