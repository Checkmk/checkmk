// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableServiceGroups_h
#define TableServiceGroups_h

#include "config.h"  // IWYU pragma: keep

#include <string>

#include "Row.h"
#include "Table.h"
class ColumnOffsets;
class MonitoringCore;
class Query;
class User;

class TableServiceGroups : public Table {
public:
    explicit TableServiceGroups(MonitoringCore *mc);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query &query, const User &user) override;
    [[nodiscard]] Row get(const std::string &primary_key) const override;

    static void addColumns(Table *table, const std::string &prefix,
                           const ColumnOffsets &offsets);
};

#endif  // TableServiceGroups_h
