// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableEventConsoleRules.h"

#include <memory>

#include "Column.h"

TableEventConsoleRules::TableEventConsoleRules(MonitoringCore *mc)
    : TableEventConsole(mc) {
    Column::Offsets offsets{};
    addColumn(std::make_unique<StringEventConsoleColumn>(
        "rule_id", "The ID of the rule", offsets));

    addColumn(std::make_unique<IntEventConsoleColumn>(
        "rule_hits", "The times rule matched an incoming message", offsets));
}

std::string TableEventConsoleRules::name() const { return "eventconsolerules"; }

std::string TableEventConsoleRules::namePrefix() const {
    return "eventconsolerules_";
}
