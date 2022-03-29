// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableColumns_h
#define TableColumns_h

#include "config.h"  // IWYU pragma: keep

#include <string>
#include <vector>

#include "Table.h"
class Column;
class MonitoringCore;
class Query;
class User;

class TableColumns : public Table {
public:
    enum class Type { table, name, description, type };

    explicit TableColumns(MonitoringCore *mc);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query, const User &user) override;

    void addTable(const Table &table);
    [[nodiscard]] std::string getValue(const Column &column, Type colcol) const;
    [[nodiscard]] std::string tableNameOf(const Column &column) const;

private:
    std::vector<const Table *> _tables;
};

#endif  // TableColumns_h
