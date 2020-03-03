// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TimePointerColumn_h
#define TimePointerColumn_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "Column.h"
#include "TimeColumn.h"
#include "opids.h"
class Filter;
class RowRenderer;

class TimePointerColumn : public TimeColumn {
public:
    TimePointerColumn(const std::string &name, const std::string &description,
                      const time_t *number, const Column::Offsets &offsets)
        : TimeColumn(name, description, offsets), _number(number) {}

private:
    const time_t *const _number;

    [[nodiscard]] std::chrono::system_clock::time_point getRawValue(
        Row /* row */) const override {
        return std::chrono::system_clock::from_time_t(*_number);
    }
};

#endif  // TimePointerColumn_h
