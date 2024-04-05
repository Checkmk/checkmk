// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableServices_h
#define TableServices_h

#include <string>

#include "livestatus/Row.h"
#include "livestatus/Table.h"
class ColumnOffsets;
class ICore;
class Query;
class User;

class TableServices : public Table {
public:
    enum class AddHosts { no, yes };

    explicit TableServices(ICore *mc);
    static void addColumns(Table *table, const std::string &prefix,
                           const ColumnOffsets &offsets, AddHosts add_hosts,
                           LockComments lock_comments,
                           LockDowntimes lock_downtimes);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query &query, const User &user,
                     const ICore &core) override;
    [[nodiscard]] Row get(const std::string &primary_key) const override;
};

#endif  // TableServices_h
