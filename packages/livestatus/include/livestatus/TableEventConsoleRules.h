// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsoleRules_h
#define TableEventConsoleRules_h

#include <string>

#include "livestatus/TableEventConsole.h"

class TableEventConsoleRules : public TableEventConsole {
public:
    TableEventConsoleRules();
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
};

#endif  // TableEventConsoleRules_h
