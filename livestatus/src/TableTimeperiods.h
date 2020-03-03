// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableTimeperiods_h
#define TableTimeperiods_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "Table.h"
#ifdef CMC
class Timeperiod;
#else
#include "nagios.h"
extern timeperiod *timeperiod_list;
#endif

class MonitoringCore;
class Query;

class TableTimeperiods : public Table {
public:
    class IRow {
    public:
        virtual ~IRow() = default;
#ifdef CMC
        virtual const Timeperiod *getTimePeriod() const = 0;
#else
        virtual const timeperiod *getTimePeriod() const = 0;
#endif
    };
    explicit TableTimeperiods(MonitoringCore *mc);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query) override;
};

#endif  // TableTimeperiods_h
