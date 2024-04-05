// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsoleStatus_h
#define TableEventConsoleStatus_h

#include <string>

#include "livestatus/Row.h"
#include "livestatus/TableEventConsole.h"
class ICore;

class TableEventConsoleStatus : public TableEventConsole {
public:
    explicit TableEventConsoleStatus(ICore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    [[nodiscard]] Row getDefault(const ICore &core) const override;
};

#endif  // TableEventConsoleStatus_h
