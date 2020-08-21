// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TimeperiodColumn_h
#define TimeperiodColumn_h

#include "config.h"  // IWYU pragma: keep

#include <cstdint>

#include "IntColumn.h"
#include "contact_fwd.h"
class Row;

class TimeperiodColumn : public IntColumn {
public:
    using IntColumn::IntColumn;
    int32_t getValue(Row row, const contact* auth_user) const override;
};

#endif  // TimeperiodColumn_h
