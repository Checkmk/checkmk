// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DynamicEventConsoleReplicationColumn_h
#define DynamicEventConsoleReplicationColumn_h

#include "config.h"  // IWYU pragma: keep

#include <memory>
#include <string>

#include "DynamicColumn.h"
class Column;
class ColumnOffsets;
class MonitoringCore;

class DynamicEventConsoleReplicationColumn : public DynamicColumn {
public:
    DynamicEventConsoleReplicationColumn(const std::string &name,
                                         const std::string &description,
                                         MonitoringCore *mc,
                                         const ColumnOffsets &);

    std::unique_ptr<Column> createColumn(const std::string &name,
                                         const std::string &arguments) override;

private:
    MonitoringCore *_mc;
};

#endif  // DynamicEventConsoleReplicationColumn_h
