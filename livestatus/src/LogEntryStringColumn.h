// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef LogEntryStringColumn_h
#define LogEntryStringColumn_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "StringColumn.h"
class Row;

class LogEntryStringColumn : public StringColumn {
public:
    using StringColumn::StringColumn;
    [[nodiscard]] std::string getValue(Row row) const override;
};

#endif  // LogEntryStringColumn_h
