// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsoleEvents_h
#define TableEventConsoleEvents_h

#include "config.h"  // IWYU pragma: keep

#include <string>

#include "TableEventConsole.h"
#include "nagios.h"
class MonitoringCore;
class Row;
class Table;

class TableEventConsoleEvents : public TableEventConsole {
public:
    explicit TableEventConsoleEvents(MonitoringCore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    static void addColumns(Table *table);
    bool isAuthorized(Row row, const contact *ctc) const override;
};

#endif  // TableEventConsoleEvents_h
