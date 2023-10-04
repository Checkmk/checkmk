// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StatsColumn_h
#define StatsColumn_h

#include <memory>

#include "livestatus/Column.h"
#include "livestatus/Filter.h"
class Aggregator;
class Logger;

class StatsColumn {
public:
    virtual ~StatsColumn() = default;
    virtual std::unique_ptr<Filter> stealFilter() = 0;
    virtual std::unique_ptr<Aggregator> createAggregator(
        Logger *logger) const = 0;
};

class StatsColumnCount : public StatsColumn {
public:
    explicit StatsColumnCount(std::unique_ptr<Filter> filter);
    std::unique_ptr<Filter> stealFilter() override;
    std::unique_ptr<Aggregator> createAggregator(Logger *logger) const override;

private:
    std::unique_ptr<Filter> _filter;
};

class StatsColumnOp : public StatsColumn {
public:
    StatsColumnOp(AggregationFactory factory, std::shared_ptr<Column> column);
    std::unique_ptr<Filter> stealFilter() override;
    std::unique_ptr<Aggregator> createAggregator(Logger *logger) const override;

private:
    AggregationFactory _factory;
    std::shared_ptr<Column> _column;
    std::unique_ptr<Filter> _filter;
};

#endif  // StatsColumn_h
