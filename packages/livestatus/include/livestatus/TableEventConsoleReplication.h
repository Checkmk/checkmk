// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableEventConsoleReplication_h
#define TableEventConsoleReplication_h

#include <string>

#include "livestatus/Table.h"
class ICore;

class TableEventConsoleReplication : public Table {
public:
    explicit TableEventConsoleReplication(ICore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query &query, const User &user,
                     const ICore &core) override;
};

#endif  // TableEventConsoleReplication_h
