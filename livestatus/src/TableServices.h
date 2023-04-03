// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableServices_h
#define TableServices_h

#include "config.h"  // IWYU pragma: keep

#include <string>

#include "livestatus/Row.h"
#include "livestatus/Table.h"
class ColumnOffsets;
class MonitoringCore;
class Query;
class User;

class TableServices : public Table {
public:
    enum class AddHosts { no, yes };

    explicit TableServices(MonitoringCore *mc);
    static void addColumns(Table *table, const std::string &prefix,
                           const ColumnOffsets &offsets, AddHosts add_hosts,
                           LockComments lock_comments,
                           LockDowntimes lock_downtimes);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query &query, const User &user) override;
    [[nodiscard]] Row get(const std::string &primary_key) const override;
};

#endif  // TableServices_h
