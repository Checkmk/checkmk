// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DoublePointerColumn_h
#define DoublePointerColumn_h

#include "config.h"  // IWYU pragma: keep
#include "Column.h"
#include "DoubleColumn.h"

class DoublePointerColumn : public DoubleColumn {
public:
    DoublePointerColumn(const std::string &name, const std::string &description,
                        const Column::Offsets &offsets, const double *number)
        : DoubleColumn(name, description, offsets), _number(number) {}
    [[nodiscard]] double getValue(Row /*unused*/) const override {
        return *_number;
    }

private:
    const double *const _number;
};

#endif  // DoublePointerColumn_h
