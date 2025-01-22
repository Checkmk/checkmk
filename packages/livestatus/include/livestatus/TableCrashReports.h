// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableCrashReports_h
#define TableCrashReports_h

#include <string>

#include "livestatus/Table.h"
class ICore;

class TableCrashReports : public Table {
public:
    explicit TableCrashReports(ICore *mc);
    [[nodiscard]] std::string name() const final;
    [[nodiscard]] std::string namePrefix() const final;
    void answerQuery(Query &query, const User &user,
                     const ICore &core) override;
};

#endif  // TableCrashReports_h
