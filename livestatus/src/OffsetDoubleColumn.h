// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef OffsetDoubleColumn_h
#define OffsetDoubleColumn_h

#include "config.h"  // IWYU pragma: keep
#include "DoubleColumn.h"
class Row;

class OffsetDoubleColumn : public DoubleColumn {
public:
    using DoubleColumn::DoubleColumn;
    [[nodiscard]] double getValue(Row row) const override;
};

#endif  // OffsetDoubleColumn_h
