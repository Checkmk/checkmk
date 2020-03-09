// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "LogEntryStringColumn.h"
#include "LogEntry.h"
#include "Row.h"

std::string LogEntryStringColumn::getValue(Row row) const {
    if (auto p = columnData<LogEntry>(row)) {
        return p->state_info();
    }
    return "";
}
