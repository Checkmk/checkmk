// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableStatus_h
#define TableStatus_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "Table.h"
#include "global_counters.h"
#ifdef CMC
class Core;
#endif
class MonitoringCore;
class Query;

class TableStatus : public Table {
public:
#ifdef CMC
    TableStatus(MonitoringCore *mc, Core *core);
#else
    explicit TableStatus(MonitoringCore *mc);
#endif

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query) override;

private:
    void addCounterColumns(const std::string &name,
                           const std::string &description, Counter which);
};

#endif  // TableStatus_h
