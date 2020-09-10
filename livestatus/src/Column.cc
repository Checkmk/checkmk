// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Column.h"

#include <utility>

#include "Logger.h"

Column::Column(std::string name, std::string description, ColumnOffsets offsets)
    : _logger(Logger::getLogger("cmk.livestatus"))
    , _name(std::move(name))
    , _description(std::move(description))
    , _offsets(std::move(offsets)) {}

const void *Column::shiftPointer(Row row) const {
    return _offsets.shiftPointer(row.rawData<void>());
}

ColumnOffsets ColumnOffsets::addIndirectOffset(int offset) const {
    ColumnOffsets result{*this};
    result.shifters_.emplace_back([offset](const void *p) {
        // TODO(sp) Figure out what is actually going on regarding nullptr...
        return p == nullptr ? nullptr : *offset_cast<const void *>(p, offset);
    });
    return result;
}

ColumnOffsets ColumnOffsets::addFinalOffset(int offset) const {
    ColumnOffsets result{*this};
    result.shifters_.emplace_back([offset](const void *p) {
        // TODO(sp) Figure out what is actually going on regarding nullptr...
        return p == nullptr ? nullptr : offset_cast<const void>(p, offset);
    });
    return result;
}

const void *ColumnOffsets::shiftPointer(const void *data) const {
    for (const auto &s : shifters_) {
        data = s(data);
    }
    return data;
}
