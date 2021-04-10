// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsoleStatus_h
#define TableEventConsoleStatus_h

#include "config.h"  // IWYU pragma: keep

#include <string>

#include "Row.h"
#include "TableEventConsole.h"
class MonitoringCore;

class TableEventConsoleStatus : public TableEventConsole {
public:
    explicit TableEventConsoleStatus(MonitoringCore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    [[nodiscard]] Row getDefault() const override;
};

#endif  // TableEventConsoleStatus_h
