// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsoleHistory_h
#define TableEventConsoleHistory_h

#include "config.h"  // IWYU pragma: keep

#include <string>

#include "TableEventConsole.h"
#include "nagios.h"
class MonitoringCore;
class Row;

class TableEventConsoleHistory : public TableEventConsole {
public:
    explicit TableEventConsoleHistory(MonitoringCore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    bool isAuthorized(Row row, const contact *ctc) const override;
};

#endif  // TableEventConsoleHistory_h
