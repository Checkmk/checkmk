// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableCrashReports_h
#define TableCrashReports_h

#include "config.h"  // IWYU pragma: keep

#include <string>

#include "Table.h"
class MonitoringCore;
class Query;
class User;

class TableCrashReports : public Table {
public:
    explicit TableCrashReports(MonitoringCore *mc);
    [[nodiscard]] std::string name() const final;
    [[nodiscard]] std::string namePrefix() const final;
    void answerQuery(Query *query, const User &user) override;
};

#endif  // TableCrashReports_h
