// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableEventConsoleRules.h"

#include <functional>
#include <memory>

#include "Column.h"
#include "IntColumn.h"
#include "Row.h"
#include "StringColumn.h"
#include "contact_fwd.h"

TableEventConsoleRules::TableEventConsoleRules(MonitoringCore *mc)
    : TableEventConsole{
          mc, [](Row /*row*/, const contact * /*auth_user*/) { return true; }} {
    ColumnOffsets offsets{};
    addColumn(
        ECRow::makeStringColumn("rule_id", "The ID of the rule", offsets));

    addColumn(ECRow::makeIntColumn(
        "rule_hits", "The times rule matched an incoming message", offsets));
}

std::string TableEventConsoleRules::name() const { return "eventconsolerules"; }

std::string TableEventConsoleRules::namePrefix() const {
    return "eventconsolerules_";
}
