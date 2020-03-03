// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DynamicRRDColumn_h
#define DynamicRRDColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include <string>
#include "Column.h"
#include "DynamicColumn.h"
#include "opids.h"
class Filter;
class MonitoringCore;

class DynamicRRDColumn : public DynamicColumn {
public:
    DynamicRRDColumn(const std::string &name, const std::string &description,
                     MonitoringCore *mc, const Column::Offsets &);

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        RelationalOperator relOp, const std::string &value) const;

    std::unique_ptr<Column> createColumn(
        const std::string &name, const std::string &arguments) override = 0;
    MonitoringCore *core();

protected:
    struct Args {
        std::string rpn;
        long int start_time;
        long int end_time;
        int resolution;
        int max_entries;
    };
    [[nodiscard]] Args parse_args(const std::string &arguments) const;

private:
    MonitoringCore *_mc;
    void invalid(const std::string &message) const;
};

#endif  // DynamicRRDColumn_h
