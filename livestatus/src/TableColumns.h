// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableColumns_h
#define TableColumns_h

#include "config.h"  // IWYU pragma: keep

#include <map>
#include <string>

#include "Table.h"
class Column;
class MonitoringCore;
class Query;

class TableColumns : public Table {
public:
    enum class Type { table, name, description, type };

    explicit TableColumns(MonitoringCore *mc);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query) override;

    void addTable(const Table &table);
    [[nodiscard]] std::string getValue(const Column &column, Type colcol) const;
    [[nodiscard]] std::string tableNameOf(const Column &column) const;

private:
    std::map<std::string, const Table *> tables_;
};

#endif  // TableColumns_h
