// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Column.h"
#include <iterator>
#include <utility>
#include "Logger.h"

Column::Column(std::string name, std::string description, Offsets offsets)
    : _logger(Logger::getLogger("cmk.livestatus"))
    , _name(std::move(name))
    , _description(std::move(description))
    , _offsets(std::move(offsets)) {}

const void *Column::shiftPointer(Row row) const {
    const void *data = row.rawData<void>();
    const auto last = std::prev(std::cend(_offsets));
    for (auto iter = std::begin(_offsets); iter != std::end(_offsets); iter++) {
        if (data == nullptr) {
            break;
        }
        if (*iter < 0) {
            continue;
        }
        data = iter == last ? offset_cast<const void>(data, *iter)
                            : *offset_cast<const void *>(data, *iter);
    }
    return data;
}
