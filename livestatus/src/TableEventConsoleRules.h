// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsoleRules_h
#define TableEventConsoleRules_h

#include "config.h"  // IWYU pragma: keep

#include <string>

#include "TableEventConsole.h"
class MonitoringCore;

class TableEventConsoleRules : public TableEventConsole {
public:
    explicit TableEventConsoleRules(MonitoringCore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
};

#endif  // TableEventConsoleRules_h
