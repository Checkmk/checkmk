// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DynamicEventConsoleReplicationColumn_h
#define DynamicEventConsoleReplicationColumn_h

#include <string>

#include "livestatus/DynamicColumn.h"
class ColumnOffsets;
class ICore;

class DynamicEventConsoleReplicationColumn : public DynamicColumn {
public:
    DynamicEventConsoleReplicationColumn(const std::string &name,
                                         const std::string &description,
                                         ICore *mc, const ColumnOffsets &);

    std::unique_ptr<Column> createColumn(const std::string &name,
                                         const std::string &arguments) override;

private:
    ICore *_mc;
};

#endif  // DynamicEventConsoleReplicationColumn_h
