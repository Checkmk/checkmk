// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsoleEvents_h
#define TableEventConsoleEvents_h

#include <string>

#include "livestatus/TableEventConsole.h"
class ICore;
class Table;

class TableEventConsoleEvents : public TableEventConsole {
public:
    explicit TableEventConsoleEvents(ICore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    static void addColumns(Table *table, const ICore &core);
};

#endif  // TableEventConsoleEvents_h
