// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableColumns_h
#define TableColumns_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include <vector>
#include "ColumnsColumn.h"
#include "Table.h"
class Column;
class MonitoringCore;
class Query;

class TableColumns : public Table {
public:
    explicit TableColumns(MonitoringCore *mc);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query) override;

    void addTable(const Table &table);
    std::string getValue(const Column *column,
                         ColumnsColumn::Type colcol) const;
    std::string tableNameOf(const Column *column) const;

private:
    std::vector<const Table *> _tables;
};

#endif  // TableColumns_h
