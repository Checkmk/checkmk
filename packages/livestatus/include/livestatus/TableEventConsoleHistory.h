// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsoleHistory_h
#define TableEventConsoleHistory_h

#include <string>

#include "livestatus/TableEventConsole.h"
class ICore;

class TableEventConsoleHistory : public TableEventConsole {
public:
    explicit TableEventConsoleHistory(ICore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
};

#endif  // TableEventConsoleHistory_h
